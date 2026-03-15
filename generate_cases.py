import csv
import random

file_path = "src/data/case_outcomes/training_dataset.csv"

case_types = [
    "dowry_harassment",
    "criminal_complaint",
    "property_dispute",
    "divorce_contested",
    "harassment_civil"
]

states = [
    "Delhi","Maharashtra","Karnataka","Punjab","Rajasthan",
    "Uttar Pradesh","Gujarat","West Bengal","Bihar","Tamil Nadu",
    "Kerala","Telangana","Andhra Pradesh","Madhya Pradesh","Assam",
    "Jharkhand","Chhattisgarh","Haryana","Odisha","Himachal Pradesh"
]

verdicts = ["convicted","acquitted","settlement","dismissed","unknown"]

severity = ["low","medium","high","critical"]

complexity = ["simple","moderate","complex","very_complex"]

first_names = [
"Amit","Rahul","Rohan","Deepak","Sanjay","Arjun","Nikhil","Vikram",
"Priya","Sneha","Anjali","Kavya","Megha","Divya","Riya","Zara"
]

last_names = [
"Sharma","Verma","Gupta","Reddy","Iyer","Nair","Patel","Singh",
"Chatterjee","Das","Joshi","Bhat","Rao","Kumar"
]

months = [
"January","February","March","April","May","June",
"July","August","September","October","November","December"
]


def generate_case():

    case_type = random.choice(case_types)
    state = random.choice(states)
    year = random.randint(2000,2024)

    case_id = "IND_" + str(random.randint(100000000,999999999))

    name1 = random.choice(first_names) + " " + random.choice(last_names)
    name2 = random.choice(first_names) + " " + random.choice(last_names)

    day = random.randint(1,28)
    month = random.choice(months)

    case_name = f"{name1} vs {name2} on {day} {month}, {year}"

    verdict = random.choice(verdicts)

    duration_days = random.randint(200,1200)

    if verdict in ["acquitted","dismissed"]:
        damages = 0
    else:
        damages = random.randint(200000,5000000)

    evidence_quality = random.randint(1,10)
    witness_count = random.randint(0,15)
    victim_docs = random.randint(0,10)
    criminal_history = random.randint(0,10)

    return [
        case_id,
        case_name,
        case_type,
        "India",
        state,
        year,
        verdict,
        duration_days,
        damages,
        evidence_quality,
        witness_count,
        victim_docs,
        criminal_history,
        random.choice(severity),
        random.choice(complexity),
        random.choice([True,False]),
        "generated",
        "synthetic_generation"
    ]


rows = []

for _ in range(200):  # number of new rows
    rows.append(generate_case())


with open(file_path, "a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print("✅ 200 new cases added successfully!")