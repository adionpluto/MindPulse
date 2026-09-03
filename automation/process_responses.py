import os
import sys
import json
import re
import argparse
from datetime import datetime, timezone
import urllib.request
import csv
import io

GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSeHTq7AJaWnuY1S7jnSrSzAU9U6klFItG0h-KqO-3gWt44p7g/viewform"

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def parse_likert(val, likert_map):
    if isinstance(val, (int, float)):
        return max(1, min(5, float(val)))
    if not isinstance(val, str):
        return 3.0
    val_clean = val.strip().lower()
    for k, v in likert_map.items():
        if k in val_clean:
            return float(v)
    match = re.search(r'\b([1-5])\b', val_clean)
    if match:
        return float(match.group(1))
    return 3.0

def score_submission(submission, config):
    likert_map = config.get('likert_map', {})
    keywords = config.get('question_keywords', {})
    answers = submission.get('answers', {})

    dim_scores = {
        'stress_anxiety': [],
        'emotional_wellbeing': [],
        'energy_vitality': [],
        'coping_adaptability': [],
        'social_connectivity': []
    }

    open_stressors = []
    open_anchors = []

    for q_text, ans_val in answers.items():
        q_lower = q_text.lower()
        ans_str = str(ans_val)

        if any(w in q_lower for w in ['source', 'concern', 'worry', 'cause', 'stressor']):
            if len(ans_str) > 3 and ans_str.lower() not in likert_map:
                open_stressors.append(ans_str)
        if any(w in q_lower for w in ['peace', 'calm', 'relax', 'activity', 'habit', 'hobby']):
            if len(ans_str) > 3 and ans_str.lower() not in likert_map:
                open_anchors.append(ans_str)

        matched_dim = None
        for dim, kw_list in keywords.items():
            if any(kw in q_lower for kw in kw_list):
                matched_dim = dim
                break

        score_val = parse_likert(ans_str, likert_map)
        if matched_dim:
            dim_scores[matched_dim].append(score_val)

    final_scores = {}
    for dim in ['stress_anxiety', 'emotional_wellbeing', 'energy_vitality', 'coping_adaptability', 'social_connectivity']:
        scores = dim_scores[dim]
        if scores:
            avg_raw = sum(scores) / len(scores)
            pct = round(((avg_raw - 1.0) / 4.0) * 100)
        else:
            pct = 50
        final_scores[dim] = max(5, min(100, pct))

    stress = final_scores['stress_anxiety']
    emotional = final_scores['emotional_wellbeing']
    energy = final_scores['energy_vitality']
    coping = final_scores['coping_adaptability']

    assigned_persona = None
    personas = config.get('personas', [])
    for p in personas:
        cond = p.get('condition', 'default')
        if cond == 'default':
            if not assigned_persona:
                assigned_persona = p
            continue
        try:
            if eval(cond, {}, {'stress': stress, 'emotional': emotional, 'energy': energy, 'coping': coping}):
                assigned_persona = p
                break
        except Exception:
            pass

    if not assigned_persona:
        assigned_persona = personas[-1] if personas else {
            'title': 'The Balanced Harmonizer',
            'tagline': 'Steady Emotional Baseline',
            'summary': 'Maintaining a steady psychological baseline with opportunities for routine enhancement.'
        }

    if stress <= 30:
        stress_label = 'Optimal / Low Tension'
        badge_type = 'success'
        badge_text = 'Thriving / Low Stress'
        stress_color = '#10b981'
        stress_advice = 'Your current stress baseline is exceptionally healthy. Focus on maintaining your restorative recovery rituals.'
    elif stress <= 50:
        stress_label = 'Moderate / Balanced'
        badge_type = 'primary'
        badge_text = 'Balanced / Manageable'
        stress_color = '#3b82f6'
        stress_advice = 'Stress levels are currently balanced and within healthy adaptive thresholds for daily productivity.'
    elif stress <= 70:
        stress_label = 'Elevated / Strained'
        badge_type = 'warning'
        badge_text = 'Elevated Strain'
        stress_color = '#f59e0b'
        stress_advice = 'Cognitive strain is noticeably elevated. Prioritize active de-escalation and micro-rest intervals.'
    else:
        stress_label = 'Severe / Overwhelmed'
        badge_type = 'danger'
        badge_text = 'High Stress / Immediate Care'
        stress_color = '#ef4444'
        stress_advice = 'Nervous system load is high. Immediate physiological decompression and schedule decompression are strongly recommended.'

    recs_pool = config.get('recommendations', {})
    action_cards = []
    priority_dims = []
    if stress >= 60:
        priority_dims.append('stress_anxiety')
    if energy <= 50:
        priority_dims.append('energy_vitality')
    if coping <= 50:
        priority_dims.append('coping_adaptability')
    if emotional <= 55:
        priority_dims.append('emotional_wellbeing')
    if not priority_dims:
        priority_dims = ['stress_anxiety', 'energy_vitality', 'emotional_wellbeing']

    phases = ['Phase 1: Immediate Relief (Day 1)', 'Phase 2: Short-Term Habit (Week 1)', 'Phase 3: Sustainable Growth (Month 1+)']
    for i, phase_title in enumerate(phases):
        dim_key = priority_dims[i % len(priority_dims)]
        dim_recs = recs_pool.get(dim_key, [])
        rec_item = dim_recs[i % len(dim_recs)] if dim_recs else {
            'action': 'Mindful Rest & Recharging',
            'detail': 'Allocate 15 minutes of uninterrupted quiet reflection and gentle physical stretching.'
        }
        card_html = f'<div class="plan-card"><div class="plan-phase">{phase_title}</div><h3 class="plan-heading">{rec_item.get("action", "Wellness Micro-Habit")}</h3><p class="plan-body">{rec_item.get("detail", "")}</p></div>'
        action_cards.append(card_html)

    return {
        'scores': final_scores,
        'persona': assigned_persona,
        'stress_label': stress_label,
        'badge_type': badge_type,
        'badge_text': badge_text,
        'stress_color': stress_color,
        'stress_advice': stress_advice,
        'open_stressors': '; '.join(open_stressors) if open_stressors else 'Academic workload, exams, routine pressures.',
        'open_anchors': '; '.join(open_anchors) if open_anchors else 'Music, physical exercise, quiet personal time.',
        'action_cards_html': '\n'.join(action_cards)
    }

def render_report(submission, scored, template_str):
    scores = scored['scores']
    sub_id = submission.get('submission_id', 'user-01')
    ts = submission.get('timestamp', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    date_str = ts.split('T')[0] if 'T' in ts else ts
    cohort = submission.get('cohort', 'Community Cohort 2026')
    radar_stress_inv = max(5, 100 - scores['stress_anxiety'])

    def get_color(val):
        if val >= 70: return '#10b981'
        if val >= 50: return '#3b82f6'
        if val >= 35: return '#f59e0b'
        return '#ef4444'

    rendered = template_str
    rendered = rendered.replace('{{participant_id}}', sub_id)
    rendered = rendered.replace('{{assessment_date}}', date_str)
    rendered = rendered.replace('{{cohort}}', cohort)
    rendered = rendered.replace('{{persona_title}}', scored['persona']['title'])
    rendered = rendered.replace('{{persona_tagline}}', scored['persona']['tagline'])
    rendered = rendered.replace('{{persona_summary}}', scored['persona']['summary'])
    rendered = rendered.replace('{{status_badge_type}}', scored['badge_type'])
    rendered = rendered.replace('{{status_badge_text}}', scored['badge_text'])

    rendered = rendered.replace('{{score_stress}}', str(scores['stress_anxiety']))
    rendered = rendered.replace('{{color_stress}}', scored['stress_color'])
    rendered = rendered.replace('{{score_emotional}}', str(scores['emotional_wellbeing']))
    rendered = rendered.replace('{{color_emotional}}', get_color(scores['emotional_wellbeing']))
    rendered = rendered.replace('{{score_energy}}', str(scores['energy_vitality']))
    rendered = rendered.replace('{{color_energy}}', get_color(scores['energy_vitality']))
    rendered = rendered.replace('{{score_coping}}', str(scores['coping_adaptability']))
    rendered = rendered.replace('{{color_coping}}', get_color(scores['coping_adaptability']))

    rendered = rendered.replace('{{radar_stress_inv}}', str(radar_stress_inv))
    rendered = rendered.replace('{{score_social}}', str(scores['social_connectivity']))
    rendered = rendered.replace('{{stress_level_label}}', scored['stress_label'])
    rendered = rendered.replace('{{stress_advice_snippet}}', scored['stress_advice'])

    rendered = rendered.replace('{{reported_stressors}}', scored['open_stressors'])
    rendered = rendered.replace('{{reported_coping_anchors}}', scored['open_anchors'])
    rendered = rendered.replace('{{action_plan_cards}}', scored['action_cards_html'])

    return rendered

def render_index(all_evaluations, index_template_str):
    total = len(all_evaluations)
    if total > 0:
        avg_stress = round(sum(e['scored']['scores']['stress_anxiety'] for e in all_evaluations) / total)
        avg_resil = round(sum(e['scored']['scores']['emotional_wellbeing'] for e in all_evaluations) / total)
        avg_coping = round(sum(e['scored']['scores']['coping_adaptability'] for e in all_evaluations) / total)
    else:
        avg_stress, avg_resil, avg_coping = 0, 0, 0

    cards_html = []
    for item in all_evaluations:
        sub = item['submission']
        scored = item['scored']
        sub_id = sub.get('submission_id', 'user-01')
        scores = scored['scores']
        badge_type = scored['badge_type']
        badge_text = scored['badge_text']
        persona_title = scored['persona']['title']
        persona_tagline = scored['persona']['tagline']

        card = f'''<a href="reports/{sub_id}.html" class="report-preview-card"><div><div class="report-card-top"><span class="user-badge">{sub_id}</span><span class="status-badge" style="background: rgba(79, 70, 229, 0.1); color: var(--brand-primary);">{badge_text}</span></div><div class="report-card-title">{persona_title}</div><div class="report-card-tagline">{persona_tagline}</div></div><div class="report-metrics-row"><div class="report-metric-item">Stress: <strong>{scores["stress_anxiety"]}%</strong></div><div class="report-metric-item">Resilience: <strong>{scores["emotional_wellbeing"]}%</strong></div><div class="report-metric-item">Vitality: <strong>{scores["energy_vitality"]}%</strong></div></div></a>'''
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
            if 'submission_id' not in new_sub:
                new_sub['submission_id'] = f'user-{len(existing_responses)+1:02d}'
            replaced = False
            for idx, item in enumerate(existing_responses):
                if item.get('submission_id') == new_sub['submission_id']:
                    existing_responses[idx] = new_sub
                    replaced = True
                    break
            if not replaced:
                existing_responses.append(new_sub)
            print(f'Added new submission: {new_sub["submission_id"]}')
        except Exception as e:
            print(f'Error parsing single payload: {e}')

    if args.sheet_csv_url:
        try:
            print(f'Fetching responses from Google Sheet: {args.sheet_csv_url}')
            req = urllib.request.Request(args.sheet_csv_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp:
                csv_content = resp.read().decode('utf-8')
                reader = csv.DictReader(io.StringIO(csv_content))
                for idx, row in enumerate(reader, 1):
                    sub_id = f'user-{idx:02d}'
                    ts = row.get('Timestamp', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
                    answers = {k: v for k, v in row.items() if k != 'Timestamp'}
                    sub_obj = {
                        'submission_id': sub_id,
                        'timestamp': ts,
                        'participant_name': f'Participant {idx:02d}',
                        'cohort': 'CEP Cohort 2026',
                        'answers': answers
                    }
                    replaced = False
                    for i, it in enumerate(existing_responses):
                        if it.get('submission_id') == sub_id:
                            existing_responses[i] = sub_obj
                            replaced = True
                            break
                    if not replaced:
                        existing_responses.append(sub_obj)
        except Exception as e:
            print(f'Error reading Google Sheet CSV: {e}')

    all_evaluations = []
    for sub in existing_responses:
        sub_id = sub.get('submission_id', 'user-01')
        scored = score_submission(sub, config)
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
        print(f'Generated report for {sub_id} -> {report_file}')

    index_html = render_index(all_evaluations, index_tpl)
    index_file = os.path.join(base_dir, 'index.html')
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(index_html)
    print(f'Generated root index.html with {len(all_evaluations)} reports')

    save_json(responses_path, existing_responses)
    print(f'Saved {len(existing_responses)} responses to {responses_path}')

if __name__ == '__main__':
    main()
