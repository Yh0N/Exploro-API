import os

def replace_in_file(filepath):
    print(f"Revisando {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Reemplazos cuidadosos
    new_content = content.replace('__tablename__ = "reseñas"', '__tablename__ = "resenas"')
    new_content = new_content.replace('id_reseña', 'id_resena')
    new_content = new_content.replace('back_populates="reseñas"', 'back_populates="resenas"')
    new_content = new_content.replace('reseñas = ', 'resenas = ')
    new_content = new_content.replace('total_reseñas', 'total_resenas')
    new_content = new_content.replace('from sqlalchemy import func, any_', 'from sqlalchemy import func')
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Modificado {filepath}")

for root, dirs, files in os.walk(r'c:\Users\jhon1\Desktop\Trabajo de Grado\exploro-api\app'):
    for file in files:
        if file.endswith('.py'):
            replace_in_file(os.path.join(root, file))
