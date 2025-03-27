from flask import Flask, request,Response
from flask_restx import Api, Resource, fields,reqparse
from flask_cors import CORS
from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient
import openai
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
import requests  # Used to set timeouts
from azure.core.pipeline.transport import RequestsTransport
from azure.core.pipeline.policies import RetryPolicy
import socket
from azure.core.exceptions import AzureError
import io
import pdfplumber
import re
from openai_prompt import process_json_content_text,process_json_content_table
import json
import json
#socket.setdefaulttimeout(5) 
# Configure a custom retry policy ssss
transport = RequestsTransport(
    connection_timeout=3,  # Enforce connection timeout
    read_timeout=3,  # Limit read time to 3 seconds
    retry_policy=RetryPolicy(total=0)  # Disable automatic retries
)
# Configure the transport settings
app = Flask(__name__)
CORS(app)

api = Api(app, version='1.0', title='Data Manipulation API',
          description='Legal Document Insights APIS',
          doc='/swagger/')

ns = api.namespace('config', description='Azure Configurations')

# Define request models for Swagger
storage_model = api.model('AzureStorageConfig', {
    'azure_storage_connection_string': fields.String(required=True, description="Azure Storage Connection String"),
})

openai_model = api.model('AzureOpenAIConfig', {
    'azure_openai_api_key': fields.String(required=True, description="Azure OpenAI API Key"),
    'azure_openai_endpoint': fields.String(required=True, description="Azure OpenAI Endpoint"),
    'azure_openai_api_version': fields.String(required=True, description="Azure OpenAI API version"),
    'azure_openai_deployment': fields.String(required=True, description="Azure OpenAI deployment"),
})

doc_intelligence_model = api.model('AzureDocumentIntelligenceConfig', {
    'azure_di_endpoint': fields.String(required=True, description="Azure Document Intelligence Endpoint"),
    'azure_di_api_key': fields.String(required=True, description="Azure Document Intelligence API Key"),
})


# 1️⃣ Azure Storage Configuration
@ns.route('/storage')
class ConfigureStorage(Resource):
    @api.expect(storage_model)
    def post(self):
        """Configure Azure Storage"""
        data = request.json
    

# Set a global timeout to limit network delays


        try:
            blob_service_client = BlobServiceClient.from_connection_string(
                data['azure_storage_connection_string'], transport=transport
            )
            
            # Check service properties with a timeout
            blob_service_client.get_service_properties(timeout=3)

            return {"message": "Azure Storage configured successfully!"}, 200

        except AzureError as az_err:
            return {"message": "Azure Storage configuration failed", "error": str(az_err)}, 400

        except requests.exceptions.RequestException as req_err:
            return {"message": "Network issue with Azure Storage", "error": str(req_err)}, 503

        except socket.timeout:
            return {"message": "Azure Storage connection timed out!"}, 408

        except Exception as e:
            return {"message": "Unexpected error occurred", "error": str(e)}, 500


# 2️⃣ Azure OpenAI Configuration
@ns.route('/openai')
class ConfigureOpenAI(Resource):
    @api.expect(openai_model)
    def post(self):
        """Configure Azure OpenAI"""
        data = request.json
        try:
             # Validate required keys
            required_keys = ['azure_openai_api_key', 'azure_openai_endpoint','azure_openai_deployment','azure_openai_api_version']
            if not all(key in data for key in required_keys):
                return {"message": "Missing required parameters!"}, 400

            # Set Azure OpenAI credentials
            # Set Azure OpenAI credentials
            openai.api_key = data['azure_openai_api_key']
            openai.api_base = data['azure_openai_endpoint']
            openai.api_version = data['azure_openai_api_version']
            openai.api_type = "azure"  # Necessary for Azure OpenAI

            deployment_name = data['azure_openai_deployment']  # Required for Azure OpenAI

            # Test API connection
            response = openai.ChatCompletion.create(  # ✅ CORRECT Azure OpenAI Syntax
                engine=deployment_name,  # Use 'engine' instead of 'model' for Azure
                messages=[{"role": "system", "content": "Say hello!"}],
                max_tokens=5
            )


            return {"message": "Azure OpenAI configured successfully!", "sample_response": response}, 200

           
        except openai.AuthenticationError:
            return {"message": "Invalid OpenAI API key!"}, 401
        except openai.OpenAIError as e:  # Generic OpenAI errors
            return {"message": "Azure OpenAI configuration failed", "error": str(e)}, 400
        except Exception as e:
            return {"message": "Unexpected error occurred", "error": str(e)}, 500
# 3️⃣ Azure Document Intelligence Configuration
@ns.route('/document-intelligence')
class ConfigureDocumentIntelligence(Resource):
    @api.expect(doc_intelligence_model)
    def post(self):
        """Configure Azure Document Intelligence"""
        data = request.json
        try:
            
            # Validate required keys
            required_keys = ['azure_di_api_key', 'azure_di_endpoint']
            if not all(key in data for key in required_keys):
                return {"message": "Missing required parameters!"}, 400

            # Extract parameters
            api_key = data['azure_di_api_key']
            endpoint = data['azure_di_endpoint']
            api_version = '2023-07-31'

            # Test API connection with a simple request (GET available models)
            test_url = f"{endpoint}/formrecognizer/documentModels?api-version={api_version}"

            headers = {
                "Ocp-Apim-Subscription-Key": api_key
            }

            response = requests.get(test_url, headers=headers, timeout=10)

            # Check if request is successful
            if response.status_code == 200:
                return {"message": "Azure Document Intelligence configured successfully!"}, 200
            else:
                return {"message": "Failed to connect to Azure Document Intelligence", "error": response.text}, response.status_code

        except requests.exceptions.Timeout:
            return {"message": "Azure Document Intelligence request timed out!"}, 408
        except requests.exceptions.RequestException as e:
            return {"message": "Azure Document Intelligence configuration failed", "error": str(e)}, 400
        except Exception as e:
            return {"message": "Unexpected error occurred", "error": str(e)}, 500


# New namespace for Data Load
data_load_ns = api.namespace('Data-Load', description='Data Load Operations')

# Define models for Swagger
container_id_model = api.model('ContainerId', {
    'container_id': fields.String(required=True, description="ID of the container")
})

document_id_model = api.model('DocumentId', {
    'document_id': fields.String(required=True, description="ID of the document in the container")
})

connection_string_model = api.model('ConnectionString', {
    'connection_string': fields.String(required=True, description="Azure Blob Storage connection string")
})
document_request_model = api.model('DocumentRequest', {
    'connection_string': fields.String(required=True, description='Azure Storage connection string'),
    'container_name': fields.String(required=True, description='Name of the Azure Storage container')
})

document_download_model = api.model('DocumentDownloadRequest', {
    'connection_string': fields.String(required=True, description='Azure Storage connection string'),
    'container_name': fields.String(required=True, description='Name of the Azure Storage container'),
    'document_name': fields.String(required=True, description='Name of the document to download')
})
@data_load_ns.route('/containers')
class GetContainers(Resource):
    @api.expect(connection_string_model)
    def post(self):
        """Get the list of containers."""
        data = request.json
        connection_string = data.get('connection_string')  # Or SAS token if passing SAS token

        if not connection_string:
            return {"message": "Connection string is required."}, 400

        try:
            # Use the provided connection string or SAS token
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            containers = blob_service_client.list_containers()
            container_list = [container.name for container in containers]
            return {"containers": container_list}, 200
        except AzureError as az_err:
            return {"message": "Error retrieving containers", "error": str(az_err)}, 400
        except requests.exceptions.RequestException as req_err:
            return {"message": "Network issue with Azure Storage", "error": str(req_err)}, 503
        except socket.timeout:
            return {"message": "Connection timed out!"}, 408
        except Exception as e:
            return {"message": "Unexpected error occurred", "error": str(e)}, 500
# 2️⃣ Get Documents from Container
@data_load_ns.route('/documents')
class GetDocuments(Resource):
    @api.expect(document_request_model)  # Ensure document_request_model includes connection_string and container_name
    def post(self):
        """Get the documents from a specified container using the connection string."""
        data = request.json
        connection_string = data.get('connection_string')
        container_name = data.get('container_name')

        if not connection_string:
            return {"message": "Connection string is required."}, 400
        if not container_name:
            return {"message": "Container name is required."}, 400

        try:
            # Use the provided connection string
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            container_client = blob_service_client.get_container_client(container_name)
            blobs = container_client.list_blobs()
            document_list = [blob.name for blob in blobs]
            return {"documents": document_list}, 200
        except AzureError as az_err:
            return {"message": f"Error retrieving documents from container {container_name}", "error": str(az_err)}, 400
        except requests.exceptions.RequestException as req_err:
            return {"message": "Network issue with Azure Storage", "error": str(req_err)}, 503
        except socket.timeout:
            return {"message": "Connection timed out!"}, 408
        except Exception as e:
            return {"message": "Unexpected error occurred", "error": str(e)}, 500


@data_load_ns.route('/documents/download')
class DownloadDocument(Resource):
    @api.expect(document_download_model)
    def post(self):
        """Download a specific document from the container."""
        data = request.json
        connection_string = data.get('connection_string')
        container_name = data.get('container_name')
        document_name = data.get('document_name')

        if not connection_string:
            return {"message": "Connection string is required."}, 400
        if not container_name:
            return {"message": "Container name is required."}, 400
        if not document_name:
            return {"message": "Document name is required."}, 400

        try:
            # Use the provided connection string
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            container_client = blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(document_name)
            
            # Download the document as a byte stream
            download_stream = blob_client.download_blob()
            document_content = download_stream.readall()

            # Return the file as a response
            return Response(
                document_content,
                content_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={document_name}"}
            )

        except AzureError as az_err:
            return {"message": f"Error downloading document {document_name} from container {container_name}", "error": str(az_err)}, 400
        except requests.exceptions.RequestException as req_err:
            return {"message": "Network issue with Azure Storage", "error": str(req_err)}, 503
        except socket.timeout:
            return {"message": "Connection timed out!"}, 408
        except Exception as e:
            return {"message": "Unexpected error occurred", "error": str(e)}, 500


data_processing = api.namespace('Document-Preprocessing', description='Document Processing API')
# extract_model = api.model('ExtractText', {
#     'file': fields.Upload(required=True, description='Select a PDF file to upload')
# })

upload_parser = reqparse.RequestParser()
upload_parser.add_argument('file', location='files', type='file', required=True, help='Select a PDF file to upload')
upload_parser.add_argument('section_pattern', location='form', type=str, required=False, help='section pattern',default=r"^(\d+\.)\s+(.*)")
upload_parser.add_argument('subsection_pattern', location='form', type=str, required=False, help='subsection pattern',default=r"^(\d+\.\d+)\.?\s+(.+)")
upload_parser.add_argument('bullet_pattern', location='form', type=str, required=False, help='bullet pattern ',default=r"^\s*([a-z])\.?\s+(.+)")

@data_processing.route('/extract-text')
class ExtractText(Resource):
    @api.expect(upload_parser)
    def post(self):
        """Extract text from a PDF file"""
        file = request.files.get('file')
        print(file)
        if not file:
            return {"message": "No file provided"}, 400
        
        try:
            text = ""
            
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            
            data1 = request.form.get('bullet_pattern')  # This will get the JSON data passed as a string in form-data
            print(data1)
            

            print(request.form.get("section_pattern"))
            section_pattern = request.form.get("section_pattern")
            subsection_pattern = request.form.get("subsection_pattern")
            bullet_pattern = request.form.get("bullet_pattern")
            print(subsection_pattern)
            try:
                print("22")
                formatted_text = self.format_to_structure(text, section_pattern, subsection_pattern, bullet_pattern)
                
            except Exception as e:
                print(11)
                return {"message": "Error formatting text", "error": str(e)}, 500

            try:
                structured_json = self.parse_content_to_json(formatted_text, section_pattern, subsection_pattern, bullet_pattern)
            except Exception as e:
                return {"message": "Error parsing formatted text into JSON", "error": str(e)}, 500

            return {"formatted_JSON": structured_json}, 200


        
        except Exception as e:
            return {"message": "Error processing PDF", "error": str(e)}, 500
    def format_to_structure(self, text, section_pattern, subsection_pattern, bullet_pattern):
        """Format text into a structured form"""
        section_regex = re.compile(section_pattern)
        subsection_regex = re.compile(subsection_pattern)
        bullet_regex = re.compile(bullet_pattern, re.DOTALL | re.MULTILINE)

        formatted_text = []
        for line in text.splitlines():
            clean_line = line.strip()
            if section_regex.match(clean_line):
                formatted_text.append(f"\n{clean_line}\n")
            elif subsection_regex.match(clean_line):
                formatted_text.append(f"{clean_line}\n")
            elif bullet_regex.match(clean_line):
                formatted_text.append(f"    {clean_line}\n")
            else:
                formatted_text.append(f"        {clean_line}\n")
        return "\n".join(formatted_text)

    def parse_content_to_json(self, text, section_pattern, subsection_pattern, bullet_pattern):
        """Parse formatted text into JSON format"""
        content = {}
        current_section = None
        current_subsection = None
        current_section_number = None
        current_subsection_number = None
        accumulated_text = ""

        section_regex = re.compile(section_pattern, re.MULTILINE)
        subsection_regex = re.compile(subsection_pattern, re.MULTILINE)
        bullet_regex = re.compile(bullet_pattern, re.MULTILINE)

        lines = text.splitlines()

        for line in lines:
            line = line.strip()

            section_match = section_regex.match(line)
            if section_match:
                if accumulated_text:
                    self.add_to_content(content, current_section_number, current_section, current_subsection_number, current_subsection, accumulated_text)
                    accumulated_text = ""
                current_section_number = section_match.group(1)
                current_section = section_match.group(2).strip()
                content[f"{current_section_number} {current_section}"] = {}
                current_subsection = None
                current_subsection_number = None
                continue

            subsection_match = subsection_regex.match(line)
            if subsection_match and current_section:
                if accumulated_text:
                    self.add_to_content(content, current_section_number, current_section, current_subsection_number, current_subsection, accumulated_text)
                    accumulated_text = ""
                current_subsection_number = subsection_match.group(1)
                current_subsection = subsection_match.group(2).strip()
                content[f"{current_section_number} {current_section}"][f"{current_subsection_number} {current_subsection}"] = []
                continue

            bullet_match = bullet_regex.match(line)
            if bullet_match:
                if accumulated_text:
                    self.add_to_content(content, current_section_number, current_section, current_subsection_number, current_subsection, accumulated_text)
                    accumulated_text = ""
                bullet_content = bullet_match.group(2).strip()
                accumulated_text = f"({bullet_match.group(1)}) {bullet_content}"
            elif current_section:
                accumulated_text += " " + line

        if accumulated_text:
            self.add_to_content(content, current_section_number, current_section, current_subsection_number, current_subsection, accumulated_text)

        return content

    def add_to_content(self, content, section_num, section, subsection_num, subsection, text):
        """Helper method to append text into the correct section/subsection"""
        section_key = f"{section_num} {section}"
        subsection_key = f"{subsection_num} {subsection}" if subsection else "No Subsection"

        content.setdefault(section_key, {}).setdefault(subsection_key, []).append(text)

table_parser = reqparse.RequestParser()
table_parser.add_argument('file', location='files', type='file', required=True, help='Select a PDF file to upload')
table_parser.add_argument('endpoint', location='form', type=str, required=False, help='Azure Document Intelligence Endpoint')
table_parser.add_argument('key', location='form', type=str, required=False, help='Key')

# Initialize DocumentAnalysisClient

def is_likely_header(row):
    filtered_row = [cell for cell in row if cell not in (None, '')]
    return len(filtered_row) == 1

@data_processing.route('/extract-table')
class ExtractTable(Resource):
    @api.expect(table_parser)
    def post(self):
        """Extract tables from a PDF file"""
        file = request.files.get('file')
        endpoint = request.form.get("endpoint")
        key = request.form.get("key")
        document_analysis_client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))

        if not file:
            return {"message": "No file provided"}, 400

        try:
           print("Received file:", file.filename)  # Debugging step
           if(file):
                print("ddd",file)
                file_stream = io.BytesIO(file.read()) 
                #print("seek",file_bytes,"ddddd",file_stream)
                poller = document_analysis_client.begin_analyze_document("prebuilt-layout", file_stream)
                print("Poller status:", poller.status())

                result = poller.result()
                json_output = []
                
                with pdfplumber.open(file) as pdf:
                    no_table = 0
                    for page_idx, azure_page in enumerate(result.pages):
                        pdf_page = pdf.pages[page_idx]
                        pdfplumber_tables = pdf_page.extract_tables()
                        azure_tables = [
                            table for table in result.tables
                            if table.bounding_regions and table.bounding_regions[0].page_number == azure_page.page_number
                        ]
                        total_tables = max(len(azure_tables), len(pdfplumber_tables))
                        for table_idx in range(total_tables):
                            possible_heading = None
                            possible_subheading = None
                            rows = []
                            
                            if table_idx < len(pdfplumber_tables):
                                pdfplumber_table = pdfplumber_tables[table_idx]
                                if pdfplumber_table:
                                    if is_likely_header(pdfplumber_table[0]):
                                        possible_heading = [cell for cell in pdfplumber_table[0] if cell not in (None, '')]
                                    if len(pdfplumber_table) > 1 and is_likely_header(pdfplumber_table[1]):
                                        possible_subheading = [cell for cell in pdfplumber_table[1] if cell not in (None, '')]
                            
                            if table_idx < len(azure_tables):
                                azure_table = azure_tables[table_idx]
                                row_dict = {}
                                for cell in azure_table.cells:
                                    if cell.row_index not in row_dict:
                                        row_dict[cell.row_index] = []
                                    row_dict[cell.row_index].append(cell.content)
                                rows = [row_dict[key] for key in sorted(row_dict.keys())]
                            
                            json_output.append({
                                "Table_no": no_table + 1,
                                "Heading": possible_heading,
                                "Subheading": possible_subheading,
                                "Rows": rows
                            })
                            no_table += 1
                
                return {"tables": json_output}, 200

        except Exception as e:
            return {"message": "Error processing PDF", "error": str(e)}, 500


LLM_Interfacing = api.namespace("LLM-Interfacing", description="API to parse JSON and process using OpenAI")

# Define the request model

json_parser = reqparse.RequestParser()
json_parser.add_argument('file', location='files', type='file', required=True, help='Select a JSON file to upload')
json_parser.add_argument('endpoint', location='form', type=str, required=False, help='Azure Open AI Endpoint')
json_parser.add_argument('key', location='form', type=str, required=False, help='Key')

@LLM_Interfacing.route('/upload-json-text')
class JSONUploadText(Resource):
    @api.expect(json_parser)
    def post(self):
        """
        Uploads a JSON file and processes its content using OpenAI.
        """
        try:
            file = request.files.get("file")
            json_data = json.load(file)  # Parse JSON file

        # Extract 'json_data' key (if present)
            data = json_data.get("formatted_JSON")
            endpoint = request.form.get("endpoint")
            key = request.form.get("key")
            
            if not data:
                return {"error": "Invalid JSON input"}, 400

            response_data = process_json_content_text(data,endpoint,key)
            # Deserialize each string to an actual JSON object
            parsed_data = [json.loads(item) for item in response_data]

            # Now that it's valid JSON, you can pretty print the response
           # pretty_response = json.dumps(parsed_data, indent=4)
            # Return the response as JSON (formatted)
            return (parsed_data), 200
        
        except Exception as e:
            return {"error": str(e)}, 500

json_parser1 = reqparse.RequestParser()
json_parser1.add_argument('file', location='files', type='file', required=True, help='Select a JSON file to upload')
json_parser1.add_argument('endpoint', location='form', type=str, required=False, help='Azure Open AI Endpoint')
json_parser1.add_argument('key', location='form', type=str, required=False, help='Key')


@LLM_Interfacing.route('/upload-json-table')
class JSONUploadTable(Resource):
    @api.expect(json_parser1)
    def post(self):
        """
        Uploads a JSON file and processes its content using OpenAI.
        """
        try:
            file = request.files.get("file")
            file_content = file.read().decode("utf-8")  # Read file and decode
            json_data = json.loads(file_content)
      
            print("JSON Type:", type(json_data))  
           
           
           
            endpoint = request.form.get("endpoint")
            key = request.form.get("key")
            
            if not json_data:
                return {"error": "Invalid JSON input"}, 400

            response_data = process_json_content_table(json_data,endpoint,key)
            # Deserialize each string to an actual JSON object
            parsed_data = [json.loads(item) for item in response_data]

            # Now that it's valid JSON, you can pretty print the response
           # pretty_response = json.dumps(parsed_data, indent=4)
            # Return the response as JSON (formatted)
            return (parsed_data), 200
        
        except Exception as e:
            return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(debug=True)

