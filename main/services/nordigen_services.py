from uuid import uuid4
from nordigen import NordigenClient
from django.conf import settings

class OpenBankingService:
    def __init__(self):
        self.client = NordigenClient(
            secret_id=settings.GOCARDLESS_SECRET_ID,
            secret_key=settings.GOCARDLESS_SECRET_KEY
        )
        self.token_data = self.client.generate_token()
        print(self.token_data)
        self.client.token = self.token_data['access']

    def refresh_token(self):
        """refrsh expired tokens"""
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
        session = self.client.initialize_session(
            institution_id=institution_id,
            redirect_uri=redirect_uri,
            reference_id=str(uuid4())
        )
        return session.link, session.requisition_id
