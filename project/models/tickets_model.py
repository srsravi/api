from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
#from project.database.database import Base
from datetime import datetime
#Base = declarative_base()
from .base_model import BaseModel


class TicketsModel(BaseModel):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_by_user_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"),nullable=True, default=None, unique=False, index=True)
    created_by_details = relationship("CustomerModal", back_populates="all_tickets")
    
    created_by_admin_id = Column(Integer, ForeignKey("admin.id"), index=True, nullable=True)
    created_by_admin_details = relationship("AdminUser", back_populates="my_tickets")
    
    subject = Column(String(250), index=True, nullable=False)
    description = Column(Text, nullable=True)
    reference = Column(String(150), nullable=True)
    tenant_id = Column(Integer, nullable=True, default=None)
    ticketcomments = relationship("TicketCommentsModel", back_populates="ticket_details")

class TicketCommentsModel(BaseModel):
    __tablename__ = "ticket_comments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), index=True, nullable=True)
    ticket_details = relationship("TicketsModel", back_populates="ticketcomments")

    admin_id = Column(Integer, ForeignKey("admin.id"), index=True, nullable=True)
    admin_details = relationship("AdminUser", back_populates="my_comments_ticket")
    
    user_id = Column(Integer, ForeignKey("customers.id"), index=True, nullable=True)
    user_details = relationship("CustomerModal", back_populates="my_comments_ticket")
    
    
    description = Column(Text, nullable=True)
    reference = Column(String(150), nullable=True)