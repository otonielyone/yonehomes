import json
from typing import List
from flask import jsonify
from pydantic import BaseModel
from sqlalchemy import Boolean, Date, Text, create_engine, Column, Integer, String, Float
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
import pandas as pd
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

DATABASE_URL = "sqlite:///brightscrape/brightmls.db"
leads_engine = create_engine(DATABASE_URL)
leads_sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=leads_engine)
Base = declarative_base()


class Mls_leads(Base):
    __tablename__ = 'mls_leads'
    mls = Column(String(20), primary_key=True, index=True) 
    sale_amt = Column(String(100), index=True)
    list_price = Column(Float, index=True)
    owner_phone = Column(String(100), index=True)
    owner_name = Column(String(100), index=True)
    owner_names = Column(String(100), index=True)
    owner_last_name = Column(String(100), index=True)
    owner_first_name = Column(String(100), index=True)
    owner2_last_name = Column(String(100), index=True)
    owner_address = Column(String(100), index=True)
    owner_city_state = Column(String(100), index=True)
    owner_zip_code = Column(String(100), index=True)
    owner_occupied = Column(String(100), index=True)
    property_class = Column(String(50))
    status = Column(String(100), index=True)
    ownership = Column(String(100), index=True)
    listing_agreement_type = Column(String(50))
    list_agent_first_name = Column(String(100), index=True)
    list_agent_last_name = Column(String(100), index=True)
    list_office_name = Column(String(100), index=True)
    remarks_private = Column(String(100), index=True)
    notes = Column(Text, default='')    
    
    def __repr__(self):
       return '<Mls_leads {}>'.format(self.mls)


class CRM(Base):
    __tablename__ = 'crm'
    id = Column(Integer, primary_key=True, autoincrement=True)  
    name = Column(String(100), index=True)
    email = Column(String(100), index=True)
    notes = Column(Text, default='')    
    
    def __repr__(self):
       return '<CRM {}>'.format(self.name)
    

class NoteResponse(BaseModel):
    notes: List[str]


def init_db():
    db_path = 'brightscrape/brightmls.db'
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    
    if not os.path.exists(db_path):
        print("Creating database file...")
        try:
            Base.metadata.drop_all(bind=leads_engine)
            Base.metadata.create_all(bind=leads_engine)
            print("Database and tables created successfully.")
        except SQLAlchemyError as e:
            print(f"An error occurred while creating the database: {e}")
    else:
        print("Database file already exists.")    

def init_leads_db():
    try:
        with leads_sessionLocal() as db:
            logger.info("Reinitializing temporary database...")
            inspector = inspect(db.get_bind())
            if not inspector.has_table('mls_leads'):
                logger.info("Original Mls_leads table does not exist. Creating it...")
                Base.metadata.create_all(bind=db.get_bind(), tables=[Mls_leads.__table__])
                logger.info("Original Mls_leads table created.")                
    except SQLAlchemyError as e:
        logger.error(f"An error occurred while initializing the temporary database: {e}")
        
def init_crm_db():
    try:
        with leads_sessionLocal() as db:
            connection = db.get_bind()
            inspector = inspect(connection)

            if not inspector.has_table('crm'):
                logger.info("Original CRM table does not exist. Creating it...")
                Base.metadata.create_all(bind=connection, tables=[CRM.__table__])
                logger.info("Original CRM table created.")
            else:
                logger.info("Original CRM table already exists.")
    except SQLAlchemyError as e:
        logger.error(f"An error occurred while initializing the CRM database: {e}")


def get_notes_from_db(data):
    mls = data.get('mls')
    with leads_sessionLocal() as db:
        notes = db.query(Mls_leads).filter(Mls_leads.mls == mls).all() 
        return notes


#def save_notes_from_db(data):
#    with leads_sessionLocal() as db:
#        mls = data.get('mls')
#        notes = data.get('notes')
#        lead = db.session.query(Mls_leads).filter_by(mls=mls).first()
#        if lead:
#            lead.notes = notes
#            db.session.commit()
#            return {'message': 'Notes saved successfully'}
#        else:
#            return {'message': 'MLS not found'}
#

def save_notes_from_db(data):
    with leads_sessionLocal() as db:
        mls = data.get('mls')
        new_notes = data.get('notes')

        lead = db.query(Mls_leads).filter_by(mls=mls).first()
        if lead:
            if lead.notes is None or lead.notes.strip() == "":
                lead.notes = new_notes 
            else:
                lead.notes += f"\n{new_notes}"
            db.commit() 
            return {'message': 'Notes saved successfully'}
        else:
            return {'message': 'MLS not found'}


def delete_notes_from_db(data):
    with leads_sessionLocal() as db:
        mls = data.get('mls')
        lead = db.query(Mls_leads).filter_by(mls=mls).first()
        
        if lead:
            lead.notes = ''  
            db.commit() 
            return {'message': 'Notes deleted successfully'}
        else:
            return {'message': 'MLS not found'}



def save_customer_info_in_db(data):
    with leads_sessionLocal() as db:
        id = data.get('id')
        name = data.get('name')
        email = data.get('email')
        notes = data.get('notes')

        lead = db.query(CRM).filter_by(id=id).first()
        
        if lead:
            if name and name.strip():
                lead.name = name
            
            if email and email.strip():
                lead.email = email
            
            if notes is not None:
                if lead.notes is None or lead.notes.strip() == "":
                    lead.notes = notes  
                else:
                    lead.notes += f"\n{notes}"  
            
            db.commit() 
            return {'message': 'Customer information updated successfully'}
        else:
            new_lead = CRM(id=id, name=name, email=email, notes=notes)
            db.add(new_lead)
            db.commit() 
            return {'message': 'Customer information saved successfully'}


def delete_notes_from_db(data):
    with leads_sessionLocal() as db:
        id = data.get('id')
        crm = db.query(CRM).filter_by(id=id).first()  
        
        if crm:
            crm.notes = ''  
            db.commit() 
            return {'message': 'CRM info deleted successfully'}
        else:
            return {'message': 'CRM info not found'}