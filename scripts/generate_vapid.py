
import os
import json
import base64
from ecdsa import SigningKey, NIST256p

def encode_base64url(data):
    return base64.urlsafe_b64encode(data).replace(b'=', b'').decode('utf-8')

def generate_vapid_keys():
    # Use ecdsa to generate VAPID keys according to RFC 8292
    private_key = SigningKey.generate(curve=NIST256p)
    public_key = private_key.get_verifying_key()
    
    # 0x04 format specifies uncompressed public key per SEC1 standard
    pub_string = b'\x04' + public_key.to_string()
    
    private_raw = private_key.to_string()
    
    vapid_private_key = encode_base64url(private_raw)
    vapid_public_key = encode_base64url(pub_string)
    
    print("VAPID_PRIVATE_KEY=" + vapid_private_key)
    print("VAPID_PUBLIC_KEY=" + vapid_public_key)

    with open('.env', 'a') as f:
        f.write("\n# Web Push VAPID Keys\n")
        f.write(f"VAPID_PRIVATE_KEY={vapid_private_key}\n")
        f.write(f"VAPID_PUBLIC_KEY={vapid_public_key}\n")
        f.write("VAPID_SUBJECT=mailto:admin@fixlink.edu\n")
    print("Keys appended to .env successfully.")

if __name__ == '__main__':
    generate_vapid_keys()
