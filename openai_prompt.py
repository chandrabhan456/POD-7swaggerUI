
import requests

import json
# Azure OpenAI configuration
def send_to_openaiText(prompt_text,api_url, headers):
    global num_tokens
    payload = {
    "messages": [
        {
            
            "role": "system",
            "content": '''You are an AI assistant specifically tasked with exactly parsing out each section of the given legal contract documents into JSON format. Please adhere to the following strict guidelines:
                 i. **only process that prompt_text which does not contain ................................pattern, must start with(eg. 1.).
  
                1. **Extract Only the Following Elements**:
                {
                    "Major Area": "exhibit_name from prompt",
                    "Reference": "Use only the first-level section headers (e.g., '1. BACKGROUND, OBJECTIVES AND STRUCTURE') for this field. Do not include subsection names or second-level headers (like 1.2). Match sections with pattern: r'^\\d+\\.\\s+[A-Z]+\\b.*'.",
                    
                    **Manager**: "This field indicates the individual responsible for overseeing the compliance of clause deliverables. Default value should be "TBD" (To Be Decided) and can be filled later.",
                    **Owner**:   "Specify the person responsible for ensuring compliance with clause deliverables. This should also have a default value of "TBD".",
                    **Status**:  "Default this to "Green." Update this field to "Blue" if the clause is fully completed, or "Closed" if it is no longer valid or required.",
                    Risk**: "Provide a risk rating from 0.0 to 10.0, categorized as follows:
                            - Low: 0-3.9
                            - Medium: 4-7.9
                            - High: 8-10
                        The default risk rating should be "Low".",
                    **Frequency**: "Indicate the frequency of the deliverables, which can only be one of the following: Per Contract, As Required, Weekly, Bi-Monthly, Monthly, Quarterly, Semi-Annually, Annually.",
                    **Category**: "Assign a category based on the contents of the section. Valid categories only include:
                                    -Service Management
                                    -Operations
                                    -Service Levels
                                    -Category
                                    -Deliverable
                                    -DR/BCP
                                    -Contract Administration
                                    -Reports
                                    -3rd Party Vendor
                                    -Security
                                    -PMO
                                    -Asset Management
                                    -Governance
                                    -Cross Functional
                                    -Services
                                    -Event Monitoring
                                    -Software Licensing
                                    -Transition
                                    -Financials
                                    -Termination
                                    -Infrastructure
                                    -Metrics
                                    -Backup/Tape/Restore
                                    -Management
                                    -Financial Implications
                                    -SLA Reports
                                    -Patch Management
                                    -Audits
                                    -Legal Compliance
                                    -BPO
                                    -Applications
                                    -Resources
                                    -Transformation
                                    -Warranty/Licensing
                                    -Documentation
                                    -Customer Task
                                    -Audit Compliance
                                    -New Business
                                    -Survey",
                     2. Extract only the critical bullet points that discuss:
                        - Terms
                        - Obligations
                        - Liabilities
                        - Risks
                        - Confidentiality
                        - Compliance
                        - Disaster recovery
                        - Ownership or intellectual property
                        - Force majeure
                        - Other key contractual topics

                        3. If there are no critical bullet points in a subsection, return:
                        `No critical items in this subsection.               
                 "Clause Text": "Include the subsection header (e.g., '1.2 Objectives') at the start of this field as a single line. 
Then, list bullet points or clauses exactly as they appear in the prompt, preserving their original format, including numbering, labels, and structure. 
Each bullet point should be enclosed in double quotes and stored as an array, maintaining line breaks and indentation as in the input. 
For example: ['No.: 1', 'Task: Configure and manage storage systems.', 'Vendor: R, A', 'Customer: C, I']."

                    "Notes": " ",
                   "Assigned To": "NA"
                   "Task Description": "** do not create Task Description for frequency 'As Required'.if frequency is Per Contract, Weekly, Bi-Monthly, Monthly, Quarterly, Semi-Annually, Annually then make relevent task based on clause text and **length of task must be less than 30 word",
                }

 
           {
                    "Major Area": "MSA",
                    "Reference": "1. BACKGROUND, OBJECTIVES AND STRUCTURE",
                    
                    "Manager": "TBD",
                    "Owner": "NA",
                    "Status": "Green",
                    "Risk": "Medium",
                   
                    "Frequency": "As Required",
                    "Category": "Contract Administration",
                     "Clause Text": [subsection_name(ex-1.1Background, Purpose and Interpretation )
                       bullet_points as it is coming from prompt with same format ],
					"Notes":[],
                    "Assigned To": "NA",
                    "Task Description":"task genrated from openAI"
                    }
                    - Each Json Block should contain information about one subsection, i.e. if "1. BACKGROUND, OBJECTIVES AND STRUCTURE" has four subsection, All four of them should have seperate Json block containing information correspoding to their text.'''
 
        },
        {
            "role": "user",
            "content": prompt_text
        }
    ],
    "max_tokens": 4096,
    "temperature": 0.2,
    "top_p": 0.95,
    "frequency_penalty": 0,
    "presence_penalty": 0
    }
 
  
    response = requests.post(api_url, headers=headers, data=json.dumps(payload))
    
    if response.status_code == 200:
        result = response.json()
        reply = result['choices'][0]['message']['content']
        return reply
    else:
        print(f"Request failed with status code {response.status_code}: {response.text}")
        return None
 


def process_json_response(response):
    """Extracts and converts a JSON response from OpenAI's text output."""
    if response.startswith("```json"):
        response = response.strip("```json").strip("```")  # Remove formatting markers
    
    try:
        # If response is inside quotes, it's a stringified JSON, so we need to parse it
        if isinstance(response, str):
            response = json.loads(response)  # Convert string to dictionary
        
        return response  # Return the properly formatted JSON
    except json.JSONDecodeError as e:
        print("Error parsing JSON:", e)
        return None  # Handle error gracefully

def process_json_content_text(content1,endpoint,key):
   
    deployment_name = "gpt-4o"
    api_version = "2023-03-15-preview"
    api_url = f"{endpoint}openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"

    headers = {
        "Content-Type": "application/json",
        "api-key": key
    }
    exhibit_number1 = "MSA"  # Modify as needed
    result_text = []

    for section, content in content1.items():
        if isinstance(content, dict):
            for subsection, details in content.items():
                subsection = section if subsection == "No Subsection" else subsection
                
                if details and isinstance(details, list):
                    bullet_points = "\n".join(f"- {item.strip()}" for item in details)  # Strip to clean spaces
                    
                    section_str = (
                        f"exhibit_name:{exhibit_number1}\n"
                        f"section_name: {section}\n"
                        f"subsection_name:{subsection}\n"
                        f"bulletpoints:\n{bullet_points}\n"
                    )

                    if "..............." not in subsection and "1. INTRODUCTION" not in section:
                        if len(bullet_points)<3000:
                            response = send_to_openaiText(section_str,api_url,headers)
                            if response:
                                response = response.replace("", "-")
                                cleaned_response = process_json_response(response)  # Fix JSON formatting
                                if cleaned_response:
                                    result_text.append(json.dumps(cleaned_response, indent=4))  # Format properly

    return result_text

def process_json_content_table(content1,endpoint,key):
   
    deployment_name = "gpt-4o"
    api_version = "2023-03-15-preview"
    
    
    api_url = f"{endpoint}openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"

    headers1 = {
        "Content-Type": "application/json",
        "api-key": key
    }
    exhibit_number1 = "MSA"  # Modify as needed
    result_text = []

    for table in content1.get("tables", []):
        table_name = table.get("Heading", "")
        subheading = table.get("Subheading", "")
        rows = table.get("Rows", [])
        
        flag=0
        section_str = ""
        formatted_bullet_points =""
        if len(rows)==0:
          
            flag=1
           
        if len(rows) > 1:
            row_length = len(rows[1])  # Use the length of the first row as the reference
            for row in rows[1:]:  # Check all rows starting from the second row
                if len(row) != row_length:  # If the length of any row is different
                    print("Table has rows with different lengths, discarding it.")
                    flag=1
                    break  # Stop the loop if a mismatch is found
        if rows and flag==0:
          
            if len(rows[0])==1:
                headers=rows[1]
                subheading = rows[0]
            else:    
                headers = rows[0]  # First row contains column names
            for row in rows[1:]:  # Skip header row
                bullet_points = []  # Reset bullet points for each row
                
                for i, (header, value) in enumerate(zip(headers, row), start=1):
                    if(value):
                        bullet_points.append(f"{header}: {value}")  # Add new value
                formatted_bullet_points = "\n".join(bullet_points)         
                section_str = (
                            f"exhibit_name:{exhibit_number1}\n"
                              f"section_name: {table_name}\n"
                              f"subsection_name:{subheading}\n"
                              f"Clause Text: [\n" + ",\n".join(f'"{point}"' for point in formatted_bullet_points.split("\n")) + "\n]"
)
                       # output.append(f"{header}: {value}")
                         
                
                if section_str:
                        
                    response = send_to_openaiText(section_str,api_url,headers1)
                    
                    if response:
                        response = response.replace("", "-")
                        cleaned_response = process_json_response(response)  # Fix JSON formatting
                        if cleaned_response:
                            result_text.append(json.dumps(cleaned_response, indent=4))      # Format properly

            
    return result_text
