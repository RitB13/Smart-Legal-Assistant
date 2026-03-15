def simulate_action(query: str):

    text = query.lower()

    if "erase evidence" in text:
        return {
            "Risk Level": "High",
            "Law": "IPC Section 201",
            "Penalty": "Up to 7 years imprisonment",
            "Advice": "Do not destroy evidence"
        }

    if "record call" in text:
        return {
            "Risk Level": "Medium",
            "Law": "IT Act / Privacy Law",
            "Penalty": "Civil liability possible",
            "Advice": "Take consent before recording"
        }

    if "hack" in text:
        return {
            "Risk Level": "High",
            "Law": "IT Act 2000",
            "Penalty": "3 years jail + fine",
            "Advice": "Do not access accounts without permission"
        }

    if "terminate employee" in text:
        return {
            "Risk Level": "Medium",
            "Law": "Labour Law",
            "Penalty": "Wrongful termination case",
            "Advice": "Follow notice period"
        }

    return {
        "Risk Level": "Unknown",
        "Law": "Not identified",
        "Penalty": "Unknown",
        "Advice": "Consult legal professional"
    }