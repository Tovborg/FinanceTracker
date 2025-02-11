from uuid import uuid4
from django.http import Http404, HttpResponse
from nordigen import NordigenClient
from django.conf import settings
from main.models import OpenBankingRequisition

class OpenBankingService:
    def __init__(self, user):
        self.user = user
        self.client = NordigenClient(
            secret_id=settings.GOCARDLESS_SECRET_ID,
            secret_key=settings.GOCARDLESS_SECRET_KEY
        )
        self.token_data = self.client.generate_token()
        print(self.token_data)
        self.client.token = self.token_data['access']

    def refresh_token(self):
        """refresh expired tokens"""
        new_token = self.client.exchange_token(self.token_data['refresh'])
        self.client.token = new_token['access_token']
        return new_token

    def get_banks(self,country="DK"):
        """get list of banks"""
        return self.client.institution.get_institutions(country=country)
    
    def get_bank_id(self, bank_name, country="DK"):
        """get specific bank's id by bank name"""
        print(self.client.institution.get_institutions(country=country))
        return self.client.institution.get_institution_id_by_name(
            country=country,
            institution=bank_name
        )
    
    def create_bank_session(self, institution_id,redirect_uri):
        """Initiate bank session"""
        # Create reference id for session
        reference_id = str(uuid4())
        session = self.client.initialize_session(
            institution_id=institution_id,
            redirect_uri=redirect_uri,
            reference_id=reference_id
        )
        print(f"Session created: {session}")
        # Store requisition in DB
        requisition, created = OpenBankingRequisition.objects.update_or_create(
            user=self.user,
            requisition_id=session.requisition_id,
            institution_id=institution_id,
            reference_id=reference_id
        )

        print(f"Saved requisition: {requisition.requisition_id}, Institution: {requisition.institution_id}, User: {self.user}")

        return session.link, session.requisition_id, reference_id
    
    def get_requisition_by_reference(self, requisition_id, reference_id):
        """retrieve requisition by id details"""
        requisition = self.client.requisition.get_requisition_by_id(requisition_id)
        
        if requisition['reference'] == reference_id:
            return requisition
        else:
            return Http404("Unauthorized")
