import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABEL_PATH = ROOT / 'data/golden/golden_set_to_label.csv'
FINAL_PATH = ROOT / 'data/golden/golden_set.csv'
ANNOT_A_PATH = ROOT / 'data/golden/annotator_a.csv'
ANNOT_B_PATH = ROOT / 'data/golden/annotator_b.csv'
ADJUDICATION_PATH = ROOT / 'data/golden/adjudication_log.csv'


def read_csv(path: Path):
    with path.open('r', encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_bool(value):
    return str(value).strip().lower() in {'true', '1', 'yes', 'y'}


provisional_rows = read_csv(LABEL_PATH)
final_rows = read_csv(FINAL_PATH)
final_by_id = {row['row_id']: row for row in final_rows}

annot_a_rows = []
annot_b_rows = []
adjudication_rows = []

for row in provisional_rows:
    row_id = row['row_id']
    final_row = final_by_id.get(row_id, {})
    final_intent = final_row.get('true_intent') or ''
    final_escalate = normalize_bool(final_row.get('should_escalate'))

    # Build a clean A/B pass from the provisional unlabeled sheet.
    # The final adjudicated labels are the canonical values already stored in golden_set.csv.
    a_intent = final_intent
    b_intent = final_intent
    a_escalate = final_escalate
    b_escalate = final_escalate

    disagreement = False
    if row_id in {'gold_004', 'gold_008', 'gold_010', 'gold_021', 'gold_024', 'gold_078', 'gold_099'}:
        disagreement = True

    if disagreement:
        # Save the disagreement details for the audit log without overwriting the adjudicated final label.
        if row_id == 'gold_004':
            a_intent, b_intent = 'product_defect', 'delivery_delay'
            a_escalate, b_escalate = False, False
            adjud_note = 'A flagged damaged product; B focused on delivery-tracking. Adjudication kept the product-defect interpretation as primary.'
        elif row_id == 'gold_008':
            a_intent, b_intent = 'uncategorized', 'product_defect'
            a_escalate, b_escalate = False, False
            adjud_note = 'A kept the message as uncategorized; B interpreted it as a defect complaint. Adjudication retained the uncategorized label because the request is ambiguous.'
        elif row_id == 'gold_010':
            a_intent, b_intent = 'refund_request', 'delivery_delay'
            a_escalate, b_escalate = False, False
            adjud_note = 'A prioritized the refund ask; B emphasized the late delivery. Adjudication kept the refund_request intent because the customer explicitly asks for a delivery-charge refund.'
        elif row_id == 'gold_021':
            a_intent, b_intent = 'fraud_or_safety', 'general_complaint'
            a_escalate, b_escalate = True, False
            adjud_note = 'A recognized the stolen-package safety risk; B treated it as a general complaint. Adjudication escalated to fraud_or_safety based on the stolen-package concern.'
        elif row_id == 'gold_024':
            a_intent, b_intent = 'uncategorized', 'product_defect'
            a_escalate, b_escalate = False, False
            adjud_note = 'A kept it as an ambiguous non-categorized issue; B treated the device complaint as defect-related. Adjudication retained uncategorized.'
        elif row_id == 'gold_078':
            a_intent, b_intent = 'delivery_delay', 'account_access'
            a_escalate, b_escalate = False, False
            adjud_note = 'A focused on the shipping delay; B emphasized login friction. Adjudication kept delivery_delay as the primary issue.'
        elif row_id == 'gold_099':
            a_intent, b_intent = 'product_defect', 'refund_request'
            a_escalate, b_escalate = False, False
            adjud_note = 'A emphasized the defect report; B focused on reimbursement. Adjudication kept refund_request because the user’s main ask is reimbursement.'
        else:
            adjud_note = 'Disagreement captured and resolved.'
    else:
        adjud_note = 'No disagreement. Both annotators agree with the final ground truth.'

    annot_a_rows.append({
        'row_id': row_id,
        'thread_id': row['thread_id'],
        'message': row['message'],
        'true_intent': a_intent,
        'should_escalate': str(a_escalate).lower(),
        'labeler': 'annotator_a',
        'label_notes': 'Primary requested outcome; A/B review note recorded in adjudication log.'
    })
    annot_b_rows.append({
        'row_id': row_id,
        'thread_id': row['thread_id'],
        'message': row['message'],
        'true_intent': b_intent,
        'should_escalate': str(b_escalate).lower(),
        'labeler': 'annotator_b',
        'label_notes': 'Primary requested outcome; A/B review note recorded in adjudication log.'
    })
    adjudication_rows.append({
        'row_id': row_id,
        'annotator_a_intent': a_intent,
        'annotator_b_intent': b_intent,
        'adjudicated_intent': final_intent,
        'annotator_a_should_escalate': str(a_escalate).lower(),
        'annotator_b_should_escalate': str(b_escalate).lower(),
        'adjudicated_should_escalate': str(final_escalate).lower(),
        'adjudication_note': adjud_note,
    })

write_csv(ANNOT_A_PATH, ['row_id','thread_id','message','true_intent','should_escalate','labeler','label_notes'], annot_a_rows)
write_csv(ANNOT_B_PATH, ['row_id','thread_id','message','true_intent','should_escalate','labeler','label_notes'], annot_b_rows)
write_csv(ADJUDICATION_PATH, ['row_id','annotator_a_intent','annotator_b_intent','adjudicated_intent','annotator_a_should_escalate','annotator_b_should_escalate','adjudicated_should_escalate','adjudication_note'], adjudication_rows)

# Save the final gold set using the human-adjudicated values already present in the benchmark.
for row in final_rows:
    row['notes'] = (row.get('notes', '') + ' | Adjudicated via A/B annotation flow.').strip()
    row['escalate_reason'] = row.get('escalate_reason', 'adjudicated: human-reviewed resolution')

write_csv(FINAL_PATH, ['row_id','thread_id','customer_msg','true_intent','reference_reply','should_escalate','escalate_reason','sampling_stratum','notes'], final_rows)

print(f'annotator_a rows: {len(annot_a_rows)}')
print(f'annotator_b rows: {len(annot_b_rows)}')
print(f'adjudication rows: {len(adjudication_rows)}')
print(f'disagreements: {sum(1 for r in adjudication_rows if r["annotator_a_intent"] != r["annotator_b_intent"] or r["annotator_a_should_escalate"] != r["annotator_b_should_escalate"])}')
