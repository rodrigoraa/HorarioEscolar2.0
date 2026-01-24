import bcrypt

senha = "fera@123"
senha_bytes = senha.encode('utf-8')
salt = bcrypt.gensalt()
hash_bytes = bcrypt.hashpw(senha_bytes, salt)
hash_final = hash_bytes.decode('utf-8')

print(f"Sua senha: {senha}")
print(f"Seu HASH:  {hash_final}")