import M2Crypto,os,re


 
 
class Keys(object):
    def empty_callback ():
     return
     
    def __init__(self,pub=None,priv=None):
        #The point of doing the split, and the replaces, below, is to ensure we have no whitespace in the public keys.
        #Just the straight key, as a long string. No \r or \n
        M2Crypto.Rand.rand_seed (os.urandom (1024))
        self.Keys = M2Crypto.RSA
        if priv == None:
            self.privkey_bio = M2Crypto.BIO.MemoryBuffer()
            self.privkey = None
        else:
            self.privkey_bio = M2Crypto.BIO.MemoryBuffer(priv.encode('utf8'))
            self.privkey = priv.encode('utf8')
        if pub == None:
            self.pubkey_bio = M2Crypto.BIO.MemoryBuffer()
            self.pubkey = None
        else:
            self.pubkey_bio = M2Crypto.BIO.MemoryBuffer(pub.encode('utf8'))
            self.pubkey = pub.encode('utf8')
    
        # Define the combined key if we have both variables.
        # Otherwise... Don't.
        if pub != None and priv != None:
            self.combinedkey = self.privkey + '\n' + self.pubkey
            self.combinedkey = self.combinedkey.encode('utf8')
            self.combinedkey_bio = M2Crypto.BIO.MemoryBuffer(self.combinedkey)
    
        self.formatkeys()
        
    
    def formatkeys(self):
        #Format the priv and pub keys
        #Make sure we have proper linebreaks every 64 characters, and a header/footer
        
        #Strip out the headers
        #Strip out the linebreaks
        #Re-Add the Linebreaks
        #Re-add the headers
        if self.privkey is not None:
            if "-----BEGIN RSA PRIVATE KEY-----" in self.privkey:
                noHeaders=self.privkey[self.privkey.find("-----BEGIN RSA PRIVATE KEY-----")+31:self.privkey.find("-----END RSA PRIVATE KEY-----")]
            else:
                print "USING NO HEADER VERSION OF PRIVKEY"
                noHeaders = self.privkey
            noBreaks = "".join(noHeaders.split())
            withLinebreaks = "\n".join(re.findall("(?s).{,64}", noBreaks))[:-1]            
            self.privkey = "-----BEGIN RSA PRIVATE KEY-----\n" + withLinebreaks + "\n-----END RSA PRIVATE KEY-----"
        else:
            print "No PRIVKEY"
            
        if self.pubkey is not None:
            if "-----BEGIN PUBLIC KEY-----" in self.pubkey:
                noHeaders=self.pubkey[self.pubkey.find("-----BEGIN PUBLIC KEY-----")+26:self.pubkey.find("-----END PUBLIC KEY-----")]
            else:
                print "USING NO HEADER VERSION OF PUBKEY"
                noHeaders=self.pubkey
            noBreaks = "".join(noHeaders.split())
            withLinebreaks = "\n".join(re.findall("(?s).{,64}", noBreaks))[:-1]
            self.pubkey = "-----BEGIN PUBLIC KEY-----\n" + withLinebreaks + "\n-----END PUBLIC KEY-----" 
        
        if self.privkey != None and self.pubkey != None:
              self.combinedkey = self.privkey + '\n' + self.pubkey
              self.combinedkey = self.combinedkey.encode('utf8')
              self.combinedkey_bio = M2Crypto.BIO.MemoryBuffer(self.combinedkey)
     
            
    def generate(self):
        self.Keys = M2Crypto.RSA.gen_key (4096, 65537,self.empty_callback)
        self.Keys.save_key_bio(self.privkey_bio,None)
        self.Keys.save_pub_key_bio(self.pubkey_bio)
        
        #TODO- use __get_addr__ to calc these OnDemand
        self.privkey = self.privkey_bio.read().encode('utf8')         
        self.pubkey = self.pubkey_bio.read().encode('utf8') 
        
        self.combinedkey = self.privkey + '\n' + self.pubkey
        self.combinedkey = self.combinedkey.encode('utf8')    
        self.combinedkey_bio = M2Crypto.BIO.MemoryBuffer(self.combinedkey)
        self.formatkeys()
        
    def signstring(self,signstring):
        SignEVP = M2Crypto.EVP.load_key_string(self.combinedkey)
        SignEVP.sign_init()
        SignEVP.sign_update(signstring)
        StringSignature = SignEVP.sign_final().encode('base64')
        return StringSignature
        
    def verifystring(self,stringtoverify,signature):
        decodedSignature = signature.decode('base64')
        PubKey = M2Crypto.RSA.load_pub_key_bio(self.pubkey_bio)
        VerifyEVP = M2Crypto.EVP.PKey()
        VerifyEVP.assign_rsa(PubKey)
        VerifyEVP.verify_init()
        VerifyEVP.verify_update(stringtoverify)
        if VerifyEVP.verify_final(decodedSignature) == 1:
            return True
        else:
            return False
        