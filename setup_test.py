import requests
try:
    # Register
    res = requests.post("http://localhost:8000/register", json={"username":"demouser","email":"demo@test.com","password":"Demo1234!"})
    print("Register:", res.status_code, res.text)
    
    # Login
    res2 = requests.post("http://localhost:8000/auth/login", data={"username":"demouser","password":"Demo1234!"})
    print("Login:", res2.status_code)
    token = res2.json().get("access_token")
    
    # Upload 3 files
    for name in ["invoice_jan.txt", "report_feb.txt", "summary_mar.txt"]:
        with open(name, "w") as f:
            f.write(f"This is a sample document for {name}. It contains multiple lines of text to ensure the file validator correctly identifies it as a plain text document. Let's add some more filler text here to reach a reasonable byte count for magic byte detection.")
        
        with open(name, "rb") as f:
            res3 = requests.post(
                "http://localhost:8000/files/upload", 
                headers={"Authorization": f"Bearer {token}"}, 
                files={"file": (name, f, "text/plain")}
            )
            print(f"Upload {name}:", res3.status_code, res3.text)
            
    print("Test data created.")
except Exception as e:
    print("ERROR:", e)
