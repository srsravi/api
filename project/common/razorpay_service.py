# services/razorpay_service.py

import razorpay
from fastapi import HTTPException
from ..aploger import AppLogger
import hmac
import hashlib

class RazorpayClient:
    def __init__(self, key_id: str, key_secret: str):
        self.client = razorpay.Client(auth=(key_id,key_secret ))

    def create_order(self, amount: int, currency: str = "INR"):
        try:
            print(amount, amount)
            amount = amount*100
            order = self.client.order.create({
                'amount': amount,
                'currency': currency,
                'payment_capture': '1'
            })
            razorpay_order_id = order.get("id")
            razorpay_payment_id = self._generate_payment_id(razorpay_order_id)
            razorpay_signature = self._generate_signature(razorpay_order_id, razorpay_payment_id)
            
            response = {
                "razorpay_order_id": razorpay_order_id,
                #"razorpay_payment_id": razorpay_payment_id,
                #"razorpay_signature": razorpay_signature,
                "amount": amount,
                "currency": currency,
                "order": order,
                "status":True
            }
            
            return response
        except Exception as e:
            AppLogger.error(str(e))
            raise HTTPException(status_code=400, detail=f"Error creating order: {str(e)}")

    def fetch_order(self, order_id: str):
        
        try:
            order = self.client.order.fetch(order_id)
            return order
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error fetching order: {str(e)}")

    def _generate_payment_id(self, order_id: str):
        # In reality, the payment_id will be generated after the payment is completed
        return f"dummy_payment_id_{order_id}"

    # Placeholder function to "generate" signature (for demonstration purposes only)
    def _generate_signature(self, order_id: str, payment_id: str):
        # In reality, the signature is calculated based on the order_id and payment_id
        key_secret = "DuqBIo8eYeZ7QaGuHadEo4GS"  # Use your Razorpay key secret
        string = f"razorpay_order_id={order_id}|razorpay_payment_id={payment_id}"
        return hashlib.sha256(f"{string}|{key_secret}".encode('utf-8')).hexdigest()
    
    def _validate_signature(self,razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str ):
        data = razorpay_order_id + "|" + razorpay_payment_id
        generated_signature = hmac.new( "DuqBIo8eYeZ7QaGuHadEo4GS".encode('utf-8'),data.encode('utf-8'),
        hashlib.sha256).hexdigest()
        if razorpay_signature == generated_signature:
            return True
        else:
            return False
def get_razorpay_client():
    razorpay_client = RazorpayClient(key_id="rzp_test_rAye2CW0Kqx4If",  key_secret="DuqBIo8eYeZ7QaGuHadEo4GS")
    return razorpay_client
