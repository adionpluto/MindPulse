import os
import sys
import json
import re
import argparse
from datetime import datetime, timezone
import urllib.request
import csv
import io

GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSeHTq7AJaWnuY1S7jnSzAU9U6klFItG0h-KqO-3gWt44p7g/viewform"

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def slugify(text):
    text = re.sub(r'[^\w\s-]', '', str(text).strip().lower())
    slug = re.sub(r'[-\s]+', '-', text)
    return slug if slug else 'participant'

def parse_likert_val(val):
    if isinstance(val, (int, float)):
        return max(1.0, min(5.0, float(val)))
    val_clean = str(val).strip().lower()
    match = re.search(r'\b([1-5])\b', val_clean)
    if match:
        return float(match.group(1))
    if any(k in val_clean for k in ["highly likely", "almost always", "always", "strongly agree", "excellent"]):
        return 5.0
    if any(k in val_clean for k in ["likely", "often", "agree", "good"]):
        return 4.0
    if any(k in val_clean for k in ["moderate", "sometimes", "neutral", "fair"]):
        return 3.0
    if any(k in val_clean for k in ["unlikely", "rarely", "disagree"]):
        return 2.0
    if any(k in val_clean for k in ["highly unlikely", "never", "almost never", "strongly disagree", "poor"]):
        return 1.0
    return 3.0

INDICATOR_SPECS = [
    {
        "key": "sleep_quality",
        "title": "Restorative Sleep & Energy",
        "desc": "Ability to wake up feeling rested and refreshed",
        "keywords": ["sleep", "rested", "energized", "refreshed"],
        "dimension": "sleep_vitality",
        "is_stress": False
    },
    {
        "key": "self_care_time",
        "title": "Daily Personal Self-Care Time",
        "desc": "Taking dedicated personal time each day to unwind",
        "keywords": ["personal time", "for yourself", "unwind", "relax"],
        "dimension": "self_care",
        "is_stress": False
    },
    {
        "key": "happiness",
        "title": "Daily Happiness & Contentment",
        "desc": "Baseline positive emotional state in daily routine",
        "keywords": ["happy", "content", "positive in your"],
        "dimension": "emotional_wellbeing",
        "is_stress": False
    },
    {
        "key": "overwhelm",
        "title": "Workload Overwhelm & Pressure",
        "desc": "Feeling weighed down by responsibilities",
        "keywords": ["overwhelmed", "weighed down", "responsibilities", "deadlines"],
        "dimension": "stress_overwhelm",
        "is_stress": True
    },
    {
        "key": "physical_tension",
        "title": "Physical Tension & Nervousness",
        "desc": "Experiencing bodily tension or racing thoughts",
        "keywords": ["tension", "nervousness", "racing thoughts"],
        "dimension": "stress_overwhelm",
        "is_stress": True
    },
    {
        "key": "calmness",
        "title": "Composure Under Setbacks",
        "desc": "Staying calm and grounded when unexpected issues arise",
        "keywords": ["calm", "setbacks", "challenges", "grounded"],
        "dimension": "emotional_wellbeing",
        "is_stress": False
    },
    {
        "key": "focus",
        "title": "Mental Clarity & Concentration",
        "desc": "Maintaining motivation and sharp task focus",
        "keywords": ["clarity", "concentration", "focus", "mental exhaustion"],
        "dimension": "sleep_vitality",
        "is_stress": False
    },
    {
        "key": "coping_habits",
        "title": "Healthy Decompression Habits",
        "desc": "Using exercise, hobbies, walks, or mindfulness to decompress",
        "keywords": ["coping habits", "coping strategies", "exercise", "walks", "hobbies"],
        "dimension": "self_care",
        "is_stress": False
    },
    {
        "key": "support_seeking",
        "title": "Reaching Out for Support",
        "desc": "Willingness to seek guidance when facing struggles",
        "keywords": ["reach out", "friends, family", "comfort or guidance"],
        "dimension": "social_connection",
        "is_stress": False
    },
    {
        "key": "belonging",
        "title": "Community Connection & Belonging",
        "desc": "Feeling valued, respected, and socially connected",
        "keywords": ["valued", "respected", "socially connected", "belonging", "community"],
        "dimension": "social_connection",
        "is_stress": False
    },
    {
        "key": "overthinking",
        "title": "Repetitive Overthinking & Worry",
        "desc": "Getting trapped in future worry and mental loops",
        "keywords": ["overthinking", "worry", "doubt", "future outcomes"],
        "dimension": "stress_overwhelm",
        "is_stress": True
    },
    {
        "key": "optimism",
        "title": "Future Optimism & Personal Growth",
        "desc": "Feeling confident, hopeful, and motivated about future goals",
        "keywords": ["optimistic", "future", "goals", "hopeful", "growth"],
        "dimension": "emotional_wellbeing",
        "is_stress": False
    }
]

def score_submission(submission, config):
    answers = submission.get('answers', {})

    # Extract demographics
    p_name = submission.get('participant_name')
    age = submission.get('age', 'N/A')
    gender = submission.get('gender', 'N/A')

    for q_text, ans_val in answers.items():
        q_lower = q_text.lower()
        ans_str = str(ans_val).strip()
        if (not p_name or p_name == 'Participant') and any(k in q_lower for k in ['full name', 'your name', 'name']):
            p_name = ans_str
        if (age == 'N/A' or not age) and 'age' in q_lower:
            age = ans_str
        if (gender == 'N/A' or not gender) and 'gender' in q_lower:
            gender = ans_str

    # Score each of the 12 indicators
    matched_values = {}
    for spec in INDICATOR_SPECS:
        found_val = None
        for q_text, ans_val in answers.items():
            q_lower = q_text.lower()
            if any(kw in q_lower for kw in spec['keywords']):
                found_val = parse_likert_val(ans_val)
                break
        matched_values[spec['key']] = found_val if found_val is not None else 3.0

    # Dimension scores
    # Stress: Overwhelm, Physical Tension, Overthinking
    stress_raw = (matched_values['overwhelm'] + matched_values['physical_tension'] + matched_values['overthinking']) / 3.0
    stress_pct = round(((stress_raw - 1.0) / 4.0) * 100)
    stress_pct = max(5, min(95, stress_pct))

    # Emotional Wellbeing: Happiness, Calmness under setbacks, Optimism
    wb_raw = (matched_values['happiness'] + matched_values['calmness'] + matched_values['optimism']) / 3.0
    wb_pct = round(((wb_raw - 1.0) / 4.0) * 100)
    wb_pct = max(5, min(95, wb_pct))

    # Sleep & Vitality: Sleep, Mental Focus
    sleep_raw = (matched_values['sleep_quality'] + matched_values['focus']) / 2.0
    sleep_pct = round(((sleep_raw - 1.0) / 4.0) * 100)
    sleep_pct = max(5, min(95, sleep_pct))

    # Personal Time & Self Care: Self-Care time, Coping habits
    sc_raw = (matched_values['self_care_time'] + matched_values['coping_habits']) / 2.0
    sc_pct = round(((sc_raw - 1.0) / 4.0) * 100)
    sc_pct = max(5, min(95, sc_pct))

    # Social Connection: Reaching out, Belonging
    soc_raw = (matched_values['support_seeking'] + matched_values['belonging']) / 2.0
    soc_pct = round(((soc_raw - 1.0) / 4.0) * 100)
    soc_pct = max(5, min(95, soc_pct))

    final_scores = {
        "stress_overwhelm": stress_pct,
        "emotional_wellbeing": wb_pct,
        "sleep_vitality": sleep_pct,
        "self_care": sc_pct,
        "social_connection": soc_pct
    }

    # Evaluate Persona
    assigned_persona = None
    personas = config.get('personas', [])
    for p in personas:
        cond = p.get('condition', 'default')
        if cond == 'default':
            if not assigned_persona:
                assigned_persona = p
            continue
        try:
            if eval(cond, {}, {
                "stress": stress_pct,
                "wellbeing": wb_pct,
                "sleep": sleep_pct,
                "self_care": sc_pct,
                "social": soc_pct
            }):
                assigned_persona = p
                break
        except Exception:
            pass

    if not assigned_persona:
        assigned_persona = personas[-1] if personas else {
            "title": "The Steady Harmonizer",
            "tagline": "Manageable Baselines with Growth Opportunities",
            "summary": "Maintaining a steady psychological baseline with opportunities for routine enhancement."
        }

    # Stress load classification
    if stress_pct <= 30:
        stress_label = "Optimal / Low Load"
        badge_type = "success"
        badge_text = "Thriving / Optimal"
        stress_color = "#10b981"
        stress_advice = "Your stress baseline is exceptionally low and balanced. Continue prioritizing your restorative sleep and unwind routines."
    elif stress_pct <= 50:
        stress_label = "Manageable / Balanced"
        badge_type = "primary"
        badge_text = "Balanced / Steady"
        stress_color = "#3b82f6"
        stress_advice = "Nervous system load is balanced and within healthy adaptive thresholds for daily academic productivity."
    elif stress_pct <= 70:
        stress_label = "Elevated Strain"
        badge_type = "warning"
        badge_text = "Elevated Tension"
        stress_color = "#f59e0b"
        stress_advice = "Cognitive strain and thought loops are noticeably elevated. Prioritize evening mental shutdowns and active decompression."
    else:
        stress_label = "Severe Overload"
        badge_type = "danger"
        badge_text = "High Stress / Decompress"
        stress_color = "#ef4444"
        stress_advice = "Acute nervous system overload detected. Immediate physiological rest, task triage, and confiding in a mentor are strongly encouraged."

    # Generate 12 Indicator Breakdown HTML
    indicators_html = []
    scale_labels = {
        1.0: ("Highly Unlikely", "danger"),
        2.0: ("Unlikely", "warning"),
        3.0: ("Moderate / Sometimes", "primary"),
        4.0: ("Likely", "success"),
        5.0: ("Highly Likely", "success")
    }

    for spec in INDICATOR_SPECS:
        raw = matched_values[spec['key']]
        label, badge_style = scale_labels.get(round(raw), ("Moderate", "primary"))
        
        # Invert badge color for stress indicators (High stress is red, low stress is green)
        if spec['is_stress']:
            if raw >= 4.0:
                badge_style = "danger"
                badge_bg = "rgba(239, 68, 68, 0.12)"
                badge_color = "#ef4444"
            elif raw >= 3.0:
                badge_style = "warning"
                badge_bg = "rgba(245, 158, 11, 0.12)"
                badge_color = "#f59e0b"
            else:
                badge_style = "success"
                badge_bg = "rgba(16, 185, 129, 0.12)"
                badge_color = "#10b981"
        else:
            if raw >= 4.0:
                badge_bg = "rgba(16, 185, 129, 0.12)"
                badge_color = "#10b981"
            elif raw >= 3.0:
                badge_bg = "rgba(79, 70, 229, 0.12)"
                badge_color = "#4f46e5"
            else:
                badge_bg = "rgba(239, 68, 68, 0.12)"
                badge_color = "#ef4444"

        card = f'''
        <div class="indicator-item">
          <div class="indicator-top">
            <span class="indicator-name">{spec['title']}</span>
            <span class="indicator-badge" style="background:{badge_bg}; color:{badge_color};">{label}</span>
          </div>
          <div class="indicator-desc">{spec['desc']}</div>
        </div>'''
        indicators_html.append(card)

    # 3-Phase Action Plan based on lowest scoring / highest stress areas
    priority_dims = []
    if stress_pct >= 55:
        priority_dims.append("stress_overwhelm")
    if sc_pct <= 55:
        priority_dims.append("self_care")
    if sleep_pct <= 55:
        priority_dims.append("sleep_vitality")
    if wb_pct <= 60:
        priority_dims.append("emotional_wellbeing")
    if soc_pct <= 55:
        priority_dims.append("social_connection")
    if not priority_dims:
        priority_dims = ["self_care", "sleep_vitality", "emotional_wellbeing"]

    recs_pool = config.get("recommendations", {})
    action_cards = []
    phases = ["Phase 1: Immediate Relief (Day 1)", "Phase 2: Short-Term Habit (Week 1)", "Phase 3: Sustainable Growth (Month 1+)"]

    for i, phase_title in enumerate(phases):
        dim_key = priority_dims[i % len(priority_dims)]
        dim_recs = recs_pool.get(dim_key, [])
        rec_item = dim_recs[i % len(dim_recs)] if dim_recs else {
            "action": "Mindful Rest & Recharging",
            "detail": "Allocate 20 minutes of uninterrupted quiet reflection and gentle physical movement."
        }
        card_html = f'''
        <div class="plan-card">
          <div class="plan-phase">{phase_title}</div>
          <h3 class="plan-heading">{rec_item.get('action', 'Wellness Micro-Habit')}</h3>
          <p class="plan-body">{rec_item.get('detail', '')}</p>
        </div>'''
        action_cards.append(card_html)

    return {
        "participant_name": p_name or "Participant",
        "age": age,
        "gender": gender,
        "scores": final_scores,
        "persona": assigned_persona,
        "stress_label": stress_label,
        "badge_type": badge_type,
        "badge_text": badge_text,
        "stress_color": stress_color,
        "stress_advice": stress_advice,
        "indicators_html": "\n".join(indicators_html),
        "action_cards_html": "\n".join(action_cards)
    }

def render_report(submission, scored, template_str):
    scores = scored['scores']
    p_name = scored['participant_name']
    age = scored['age']
    gender = scored['gender']
    sub_id = submission.get('submission_id') or slugify(p_name)
    ts = submission.get('timestamp', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    date_str = ts.split('T')[0] if 'T' in ts else ts
    cohort = submission.get('cohort', 'CEP Cohort 2026')
    radar_stress_inv = max(5, 100 - scores['stress_overwhelm'])

    def get_color(val):
        if val >= 70: return "#10b981"
        if val >= 50: return "#3b82f6"
        if val >= 35: return "#f59e0b"
        return "#ef4444"

    rendered = template_str
    rendered = rendered.replace('{{participant_name}}', p_name)
    rendered = rendered.replace('{{participant_age}}', str(age))
    rendered = rendered.replace('{{participant_gender}}', str(gender))
    rendered = rendered.replace('{{participant_id}}', sub_id)
    rendered = rendered.replace('{{assessment_date}}', date_str)
    rendered = rendered.replace('{{cohort}}', cohort)
    rendered = rendered.replace('{{persona_title}}', scored['persona']['title'])
    rendered = rendered.replace('{{persona_tagline}}', scored['persona']['tagline'])
    rendered = rendered.replace('{{persona_summary}}', scored['persona']['summary'])
    rendered = rendered.replace('{{status_badge_type}}', scored['badge_type'])
    rendered = rendered.replace('{{status_badge_text}}', scored['badge_text'])

    rendered = rendered.replace('{{score_stress}}', str(scores['stress_overwhelm']))
    rendered = rendered.replace('{{color_stress}}', scored['stress_color'])
    rendered = rendered.replace('{{score_emotional}}', str(scores['emotional_wellbeing']))
    rendered = rendered.replace('{{color_emotional}}', get_color(scores['emotional_wellbeing']))
    rendered = rendered.replace('{{score_energy}}', str(scores['sleep_vitality']))
    rendered = rendered.replace('{{color_energy}}', get_color(scores['sleep_vitality']))
    rendered = rendered.replace('{{score_coping}}', str(scores['self_care']))
    rendered = rendered.replace('{{color_coping}}', get_color(scores['self_care']))
    rendered = rendered.replace('{{score_social}}', str(scores['social_connection']))
    rendered = rendered.replace('{{color_social}}', get_color(scores['social_connection']))

    rendered = rendered.replace('{{radar_stress_inv}}', str(radar_stress_inv))
    rendered = rendered.replace('{{stress_level_label}}', scored['stress_label'])
    rendered = rendered.replace('{{stress_advice_snippet}}', scored['stress_advice'])
    rendered = rendered.replace('{{indicators_breakdown_html}}', scored['indicators_html'])
    rendered = rendered.replace('{{action_plan_cards}}', scored['action_cards_html'])

    return rendered

def render_index(all_evaluations, index_template_str):
    total = len(all_evaluations)
    if total > 0:
        avg_stress = round(sum(e['scored']['scores']['stress_overwhelm'] for e in all_evaluations) / total)
        avg_resil = round(sum(e['scored']['scores']['emotional_wellbeing'] for e in all_evaluations) / total)
        avg_coping = round(sum(e['scored']['scores']['self_care'] for e in all_evaluations) / total)
    else:
        avg_stress, avg_resil, avg_coping = 0, 0, 0

    cards_html = []
    for item in all_evaluations:
        sub = item['submission']
        scored = item['scored']
        p_name = scored['participant_name']
        age = scored['age']
        gender = scored['gender']
        sub_id = sub.get('submission_id') or slugify(p_name)
        scores = scored['scores']
        badge_text = scored['badge_text']
        persona_title = scored['persona']['title']
        persona_tagline = scored['persona']['tagline']

        demo_str = f'{gender}' if gender != 'N/A' else ''
        if age != 'N/A':
            demo_str += f', Age {age}' if demo_str else f'Age {age}'

        card = f'''<a href="reports/{sub_id}.html" class="report-preview-card"><div><div class="report-card-top"><span class="user-badge">{p_name}</span><span class="status-badge" style="background: rgba(79, 70, 229, 0.1); color: var(--brand-primary);">{badge_text}</span></div><div class="report-card-title">{persona_title}</div><div class="report-card-tagline">{persona_tagline}</div>{f"<div style='font-size:0.75rem;color:var(--text-muted);margin-bottom:10px;'>{demo_str}</div>" if demo_str else ''}</div><div class="report-metrics-row"><div class="report-metric-item">Stress: <strong>{scores["stress_overwhelm"]}%</strong></div><div class="report-metric-item">Happiness: <strong>{scores["emotional_wellbeing"]}%</strong></div><div class="report-metric-item">Sleep: <strong>{scores["sleep_vitality"]}%</strong></div></div></a>'''
        cards_html.append(card)

    rendered = index_template_str
    rendered = rendered.replace('{{google_form_url}}', GOOGLE_FORM_URL)
    rendered = rendered.replace('{{total_participants}}', str(total))
    rendered = rendered.replace('{{avg_stress_score}}', str(avg_stress))
    rendered = rendered.replace('{{avg_resilience_score}}', str(avg_resil))
    rendered = rendered.replace('{{avg_coping_score}}', str(avg_coping))
    rendered = rendered.replace('{{report_cards_html}}', '\n'.join(cards_html))

    return rendered

def main():
    parser = argparse.ArgumentParser(description='Process Google Forms psychological responses into static HTML reports')
    parser.add_argument('--base-dir', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument('--single-payload', help='Single submission JSON string from GitHub Action dispatch')
    parser.add_argument('--sheet-csv-url', help='Public/Published Google Sheet CSV export URL')
    args = parser.parse_args()

    base_dir = args.base_dir
    config_path = os.path.join(base_dir, 'data', 'scoring_config.json')
    responses_path = os.path.join(base_dir, 'data', 'responses.json')
    sample_path = os.path.join(base_dir, 'automation', 'sample_responses.json')
    report_tpl_path = os.path.join(base_dir, 'templates', 'report_template.html')
    index_tpl_path = os.path.join(base_dir, 'templates', 'index_template.html')
    reports_out_dir = os.path.join(base_dir, 'reports')
    os.makedirs(reports_out_dir, exist_ok=True)

    config = load_json(config_path)
    with open(report_tpl_path, 'r', encoding='utf-8') as f:
        report_tpl = f.read()
    with open(index_tpl_path, 'r', encoding='utf-8') as f:
        index_tpl = f.read()

    existing_responses = load_json(responses_path)
    if not isinstance(existing_responses, list):
        existing_responses = []

    if not existing_responses and os.path.exists(sample_path):
        existing_responses = load_json(sample_path)

    if args.single_payload:
        try:
            new_sub = json.loads(args.single_payload)
            p_name = new_sub.get('participant_name', 'Participant')
            if 'submission_id' not in new_sub or not new_sub['submission_id']:
                new_sub['submission_id'] = slugify(p_name)
            replaced = False
            for idx, item in enumerate(existing_responses):
                if item.get('submission_id') == new_sub['submission_id']:
                    existing_responses[idx] = new_sub
                    replaced = True
                    break
            if not replaced:
                existing_responses.append(new_sub)
            print(f'Added new submission: {new_sub["submission_id"]} ({p_name})')
        except Exception as e:
            print(f'Error parsing single payload: {e}')

    all_evaluations = []
    for sub in existing_responses:
        scored = score_submission(sub, config)
        sub_id = sub.get('submission_id') or slugify(scored['participant_name'])
        sub['submission_id'] = sub_id
        sub['participant_name'] = scored['participant_name']
        sub['age'] = scored['age']
        sub['gender'] = scored['gender']

        html_content = render_report(sub, scored, report_tpl)

        report_file = os.path.join(reports_out_dir, f'{sub_id}.html')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        root_report_file = os.path.join(base_dir, f'{sub_id}.html')
        root_html_content = html_content.replace('../index.html', 'index.html')
        with open(root_report_file, 'w', encoding='utf-8') as f:
            f.write(root_html_content)

        all_evaluations.append({
            'submission': sub,
            'scored': scored
        })
        print(f'Generated report for {sub_id} ({scored["participant_name"]}) -> {report_file}')

    index_html = render_index(all_evaluations, index_tpl)
    index_file = os.path.join(base_dir, 'index.html')
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(index_html)
    print(f'Generated root index.html with {len(all_evaluations)} reports')

    save_json(responses_path, existing_responses)
    print(f'Saved {len(existing_responses)} responses to {responses_path}')

if __name__ == '__main__':
    main()
