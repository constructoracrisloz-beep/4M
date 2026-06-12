import sqlite3
import hashlib
import os

SECRET = 'natura-admin-secret-2026'

def main():
    db_path = os.path.join(os.path.dirname(__file__), 'natura.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. Get Wilmer's data
    c.execute("SELECT * FROM usuarios WHERE rol='worker' AND nombre LIKE '%Wilmer%'")
    wilmer = c.fetchone()
    
    if not wilmer:
        print("❌ Error: No encontré a nadie llamado 'Wilmer' en la base de datos.")
        print("Por favor verifica el nombre o créalos manualmente desde el panel.")
        return
        
    print(f"✅ Datos de {wilmer['nombre']} encontrados. Copiando perfil...")
    
    # Generate next username function
    def get_next_username():
        c.execute("SELECT username FROM usuarios WHERE username LIKE 'U%' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        import re
        if row:
            m = re.search(r'U(\d+)', row['username'])
            if m:
                return f"U{int(m.group(1)) + 1:04d}"
        return "U0001"
    
    workers = [
        {"nombre": "Edinson nonajulca Vilchez", "dni": "42170259"},
        {"nombre": "Eduardo Crisanto Lozada", "dni": "41446981"}
    ]
    
    for w in workers:
        c.execute("SELECT * FROM usuarios WHERE dni = ?", (w['dni'],))
        if c.fetchone():
            print(f"⚠️ El DNI {w['dni']} ({w['nombre']}) ya existe. Actualizando datos...")
            c.execute("""
                UPDATE usuarios 
                SET nombre=?, cargo=?, area=?, sueldo=?, fecha_ingreso=?, telefono=?, direccion=?, email=?, estado=?, foto=?
                WHERE dni=?
            """, (w['nombre'], wilmer['cargo'], wilmer['area'], wilmer['sueldo'], wilmer['fecha_ingreso'], wilmer['telefono'], wilmer['direccion'], wilmer['email'], wilmer['estado'], wilmer['foto'], w['dni']))
        else:
            uname = get_next_username()
            pw = hashlib.sha256(f"{w['dni']}{SECRET}".encode()).hexdigest()
            c.execute("""
                INSERT INTO usuarios (username, password, nombre, dni, cargo, area, sueldo, fecha_ingreso, telefono, direccion, email, estado, foto, rol)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'worker')
            """, (uname, pw, w['nombre'], w['dni'], wilmer['cargo'], wilmer['area'], wilmer['sueldo'], wilmer['fecha_ingreso'], wilmer['telefono'], wilmer['direccion'], wilmer['email'], wilmer['estado'], wilmer['foto']))
            print(f"✅ ¡Trabajador creado! {w['nombre']} | Usuario: {uname} | Clave: {w['dni']}")
            
    conn.commit()
    conn.close()
    print("🎉 ¡Completado con éxito!")

if __name__ == '__main__':
    main()
