from flask import Flask, request
from flask_restx import Api, Resource, fields
from flask_cors import CORS
from azure.storage.blob import BlobServiceClient
import openai
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
import requests  # Used to set timeouts
from azure.core.pipeline.transport import RequestsTransport
from azure.core.pipeline.policies import RetryPolicy
import socket
from azure.core.exceptions import AzureError
socket.setdefaulttimeout(3) 
# Configure a custom retry policy
transport = RequestsTransport(
    connection_timeout=3,  # Enforce connection timeout
    read_timeout=3,  # Limit read time to 3 seconds
    retry_policy=RetryPolicy(total=0)  # Disable automatic retries
)
# Configure the transport settings
#transport = RequestsTransport(retry_policy=retry_policy)
app = Flask(__name__)
CORS(app)

api = Api(app, version='1.0', title='Azure Configuration API',
          description='Configure Azure Storage, OpenAI, and Document Intelligence',
          doc='/swagger/')

ns = api.namespace('config', description='Azure Configurations')

# Define request models for Swagger
storage_model = api.model('AzureStorageConfig', {
    'azure_storage_connection_string': fields.String(required=True, description="Azure Storage Connection String"),
})

openai_model = api.model('AzureOpenAIConfig', {
    'azure_openai_api_key': fields.String(required=True, description="Azure OpenAI API Key"),
    'azure_openai_deployment': fields.String(required=True, description="Azure OpenAI Deployment Name"),
})

doc_intelligence_model = api.model('AzureDocumentIntelligenceConfig', {
    'azure_document_intelligence_endpoint': fields.String(required=True, description="Azure Document Intelligence Endpoint"),
    'azure_document_intelligence_key': fields.String(required=True, description="Azure Document Intelligence API Key"),
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
            openai.api_key = data['azure_openai_api_key']
            response = openai.Model.list(request_timeout=5)  # ⏳ Timeout added
            if response:
                return {"message": "Azure OpenAI configured successfully!"}, 200
            else:
                return {"message": "Invalid OpenAI response"}, 400
        except openai.error.AuthenticationError:
            return {"message": "Invalid OpenAI API key!"}, 401
        except openai.error.Timeout:
            return {"message": "Azure OpenAI request timed out!"}, 408
        except Exception as e:
            return {"message": "Azure OpenAI configuration failed", "error": str(e)}, 400


# 3️⃣ Azure Document Intelligence Configuration
@ns.route('/document-intelligence')
class ConfigureDocumentIntelligence(Resource):
    @api.expect(doc_intelligence_model)
    def post(self):
        """Configure Azure Document Intelligence"""
        data = request.json
        try:
            doc_intelligence_client = DocumentIntelligenceClient(
                endpoint=data['azure_document_intelligence_endpoint'],
                credential=AzureKeyCredential(data['azure_document_intelligence_key'],transport=transport)
            )
            response = doc_intelligence_client.get_info()
            return {"message": "Azure Document Intelligence configured successfully!"}, 200
        except requests.exceptions.Timeout:
            return {"message": "Azure Document Intelligence connection timed out!"}, 408
        except Exception as e:
            return {"message": "Azure Document Intelligence configuration failed", "error": str(e)}, 400


if __name__ == '__main__':
    app.run(debug=True)
