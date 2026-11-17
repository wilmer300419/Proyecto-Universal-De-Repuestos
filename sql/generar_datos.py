"""Genera sql/datos_prueba.sql: datos de ejemplo (>= 20 registros en cada una de las 26 tablas).

Uso:  python sql/generar_datos.py
El SQL resultante lo carga `flask --app run cargar-datos` sobre una base ya migrada. Es determinista (semilla fija),
salvo los hashes de contraseña, que llevan sal aleatoria.
Contraseña de todos los usuarios de ejemplo: Repuestos#2026
"""
import os
import random
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from werkzeug.security import generate_password_hash

random.seed(2026)
IVA = Decimal("0.19")
CENT = Decimal("0.01")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos_prueba.sql")
SIN_CONFLICTO = {"sale_state", "sale_type"}   # V001 ya crea los registros base de estos catálogos


def money(x):
    return Decimal(x).quantize(CENT, rounding=ROUND_HALF_UP)


def q(v):
    """Literal SQL seguro."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, Decimal)):
        return str(v)
    if isinstance(v, list):
        return "ARRAY[" + ",".join(str(int(x)) for x in v) + "]::BIGINT[]" if v else "ARRAY[]::BIGINT[]"
    if isinstance(v, datetime):
        return "'" + v.isoformat() + "'"
    return "'" + str(v).replace("'", "''") + "'"


TABLES = []  # (tabla, columnas, filas)


def table(name, cols, rows):
    TABLES.append((name, cols, rows))
    return rows


def named(rows):
    """[(nombre, descripcion)] -> filas (id, name, description, state)."""
    return [(i, n, d, True) for i, (n, d) in enumerate(rows, 1)]


# ---------------------------------------------------------------- catálogos
table("sale_state", ["sale_state_id", "name", "description", "state"], named([
    ("Pendiente", "Pedido creado, pendiente de pago"), ("Pagada", "Pago aprobado"),
    ("Despachada", "En camino al cliente"), ("Entregada", "Recibida por el cliente"),
    ("Cancelada", "Anulada antes del pago"), ("En verificación", "Pago en revisión antifraude"),
    ("En preparación", "Alistamiento en bodega"), ("Empacada", "Lista para despacho"),
    ("Retenida", "Retenida por inconsistencia en datos"), ("Devuelta", "Devuelta por el cliente"),
    ("Reembolsada", "Dinero devuelto al cliente"), ("Garantía", "En trámite de garantía"),
    ("Cotizada", "Cotización enviada al cliente"), ("Apartada", "Producto apartado con abono"),
    ("Facturada", "Factura electrónica emitida"), ("Rechazada", "Pago rechazado por la entidad"),
    ("Parcial", "Entrega parcial de productos"), ("Reprogramada", "Entrega reprogramada"),
    ("Siniestro", "Pérdida o daño en transporte"), ("Cerrada", "Proceso finalizado y archivado"),
]))

table("sale_type", ["sale_type_id", "name", "description", "state"], named([
    ("En línea", "Compra en la tienda web"), ("Mostrador", "Venta en punto físico"),
    ("Telefónica", "Pedido por línea telefónica"), ("WhatsApp", "Pedido por WhatsApp"),
    ("Mayorista", "Venta a talleres y distribuidores"), ("Taller aliado", "Pedido de taller con convenio"),
    ("Flota empresarial", "Mantenimiento de flotas"), ("Marketplace", "Venta en marketplace externo"),
    ("Cotización convertida", "Cotización aprobada"), ("Garantía", "Reposición por garantía"),
    ("Exportación", "Venta fuera del país"), ("Licitación", "Contratos públicos"),
    ("Suscripción", "Kits de mantenimiento periódicos"), ("Domicilio express", "Entrega el mismo día"),
    ("Feria automotriz", "Venta en eventos"), ("Recompra", "Cliente frecuente"),
    ("Preventa", "Producto bajo pedido"), ("Canje", "Intercambio de repuestos"),
    ("Aseguradora", "Pedido de aseguradora"), ("Interna", "Consumo interno"),
]))

table("document_type", ["document_type_id", "name", "acronym", "state"], [
    (i, n, a, True) for i, (n, a) in enumerate([
        ("Cédula de ciudadanía", "CC"), ("Cédula de extranjería", "CE"), ("NIT", "NIT"), ("Pasaporte", "PA"),
        ("Tarjeta de identidad", "TI"), ("Registro civil", "RC"), ("Permiso especial de permanencia", "PEP"),
        ("Permiso por protección temporal", "PPT"), ("Número único de identificación personal", "NUIP"),
        ("Documento de identificación extranjero", "DIE"), ("Carné diplomático", "CD"),
        ("Salvoconducto", "SC"), ("Tarjeta de extranjería", "TE"), ("Certificado de nacido vivo", "CN"),
        ("Adulto sin identificación", "AS"), ("Menor sin identificación", "MS"),
        ("NIT de otro país", "NITE"), ("Registro único tributario", "RUT"),
        ("Documento de identidad militar", "DIM"), ("Permiso de trabajo", "PT"),
    ], 1)])

DEPTS = ["Bogotá D.C.", "Antioquia", "Valle del Cauca", "Cundinamarca", "Atlántico", "Santander", "Bolívar",
         "Boyacá", "Tolima", "Huila", "Meta", "Nariño", "Caldas", "Risaralda", "Quindío", "Cauca", "Córdoba",
         "Norte de Santander", "Magdalena", "Cesar", "Sucre", "La Guajira", "Casanare", "Chocó"]
table("department", ["department_id", "name", "description", "state"],
      [(i, n, f"Departamento de {n}" if i > 1 else "Distrito Capital", True) for i, n in enumerate(DEPTS, 1)])
CITIES = [("Bogotá", 1), ("Medellín", 2), ("Cali", 3), ("Soacha", 4), ("Barranquilla", 5), ("Bucaramanga", 6),
          ("Cartagena", 7), ("Tunja", 8), ("Ibagué", 9), ("Neiva", 10), ("Villavicencio", 11), ("Pasto", 12),
          ("Manizales", 13), ("Pereira", 14), ("Armenia", 15), ("Popayán", 16), ("Montería", 17), ("Cúcuta", 18),
          ("Santa Marta", 19), ("Valledupar", 20), ("Chía", 4), ("Zipaquirá", 4), ("Envigado", 2), ("Palmira", 3)]
table("city", ["city_id", "name", "state", "department_id"], [(i, n, True, d) for i, (n, d) in enumerate(CITIES, 1)])

CAR_BRANDS = ["Chevrolet", "Renault", "Mazda", "Toyota", "Hyundai", "Kia", "Nissan", "Ford", "Volkswagen", "Suzuki",
              "Mitsubishi", "Honda", "Peugeot", "Fiat", "Jeep", "BMW", "Mercedes-Benz", "Audi", "Subaru", "Citroën",
              "Dodge", "JAC"]
table("car_brand", ["car_brand_id", "name", "description", "state"],
      named([(b, f"Vehículos {b}") for b in CAR_BRANDS]))
B = {n: i for i, n in enumerate(CAR_BRANDS, 1)}

table("car_type", ["car_type_id", "name", "description", "state"], named([
    ("Automóvil", "Sedán o compacto"), ("Camioneta", "Utilitario"), ("SUV", "Vehículo deportivo utilitario"),
    ("Pickup", "Platón de carga"), ("Hatchback", "Compacto de 5 puertas"), ("Sedán", "Tres volúmenes"),
    ("Van", "Pasajeros o carga"), ("Campero", "Todo terreno"), ("Coupé", "Dos puertas"),
    ("Convertible", "Techo descapotable"), ("Station wagon", "Familiar"), ("Crossover", "SUV compacto"),
    ("Minivan", "Familiar de 7 puestos"), ("Furgón", "Carga cerrada"), ("Camión ligero", "Hasta 3.5 t"),
    ("Buseta", "Transporte público"), ("Microbús", "Hasta 19 pasajeros"), ("Taxi", "Servicio público"),
    ("Motocarro", "Tres ruedas"), ("Deportivo", "Alto desempeño"),
]))
CT = {"auto": 1, "cam": 2, "suv": 3, "pick": 4, "hatch": 5, "sedan": 6, "cross": 12}

CCS = ["0.8L", "1.0L", "1.2L", "1.3L", "1.4L", "1.5L", "1.6L", "1.8L", "2.0L", "2.2L", "2.4L", "2.5L", "2.7L",
       "2.8L", "3.0L", "3.2L", "3.5L", "3.6L", "4.0L", "5.0L"]
table("cylinder_capacity", ["cylinder_capacity_id", "name", "state"], [(i, n, True) for i, n in enumerate(CCS, 1)])
CC = {n: i for i, n in enumerate(CCS, 1)}

CATS = ["Radiadores", "Filtros", "Frenos", "Suspensión", "Motor", "Embrague", "Encendido", "Iluminación",
        "Baterías", "Correas", "Bombas de agua", "Escape", "Dirección", "Transmisión", "Carrocería",
        "Espejos", "Amortiguadores", "Rodamientos", "Sensores", "Lubricantes"]
table("spare_part_type", ["spare_part_type_id", "name", "description", "state"],
      named([(c, f"Repuestos de {c.lower()}") for c in CATS]))
T = {n: i for i, n in enumerate(CATS, 1)}

PBRANDS = ["Genérica", "Bosch", "NGK", "Valeo", "Denso", "Gates", "Monroe", "Brembo", "Mann-Filter", "SKF",
           "Mobil", "Castrol", "Hella", "Luk", "Sachs", "Delphi", "Moog", "Mahle", "Philips", "Koyo"]
table("spare_part_brand", ["spare_part_brand_id", "name", "description", "state"],
      named([(b, "Marca de repuesto" if i else "Sin marca registrada") for i, b in enumerate(PBRANDS)]))
PB = {n: i for i, n in enumerate(PBRANDS, 1)}

# ---------------------------------------------------------------- empresa y bodegas
COMPANIES = [
    ("900123456-1", "Universal de Repuestos WG", "Calle 63F #25-49, Bogotá"),
    ("901200301-2", "Autopartes del Norte S.A.S.", "Av. Calle 134 #19-20, Bogotá"),
    ("901200302-3", "Distribuidora Radiadores Andinos", "Carrera 30 #10-15, Bogotá"),
    ("901200303-4", "Frenos y Embragues 7 de Agosto", "Calle 66 #24-31, Bogotá"),
    ("901200304-5", "Lubricantes La Sabana", "Autopista Norte km 20, Chía"),
    ("901200305-6", "Importadora Repuestos Asiáticos", "Calle 13 #68-90, Bogotá"),
    ("901200306-7", "Eléctricos Automotrices El Ricaurte", "Carrera 27 #9-40, Bogotá"),
    ("901200307-8", "Suspensiones Medellín S.A.S.", "Calle 10 #52-18, Medellín"),
    ("901200308-9", "Repuestos del Pacífico", "Calle 15 #8-60, Cali"),
    ("901200309-0", "Baterías Caribe Ltda.", "Vía 40 #71-200, Barranquilla"),
    ("901200310-1", "Rodamientos Santander", "Carrera 15 #45-12, Bucaramanga"),
    ("901200311-2", "Escapes y Silenciadores Boyacá", "Avenida Norte #50-30, Tunja"),
    ("901200312-3", "Taller Aliado Motores Tolima", "Calle 60 #5-14, Ibagué"),
    ("901200313-4", "Partes Llaneras", "Calle 38 #29-10, Villavicencio"),
    ("901200314-5", "Iluminación Automotriz Eje", "Carrera 7 #19-50, Pereira"),
    ("901200315-6", "Sensores y Electrónica Caldas", "Avenida Santander #60-40, Manizales"),
    ("901200316-7", "Transmisiones del Valle", "Carrera 1 #35-80, Palmira"),
    ("901200317-8", "Carrocerías Costa Norte", "Calle 30 #4-20, Santa Marta"),
    ("901200318-9", "Repuestos Frontera", "Avenida 0 #12-60, Cúcuta"),
    ("901200319-0", "Autopartes Sur de Bogotá", "Autopista Sur #60-30, Soacha"),
]
table("company", ["company_id", "tax_id", "name", "address", "phone", "cellphone", "email", "state"], [
    (i, nit, n, a, f"601{random.randint(2000000, 7999999)}", "3104772730" if i == 1 else f"31{random.randint(10000000, 99999999)}",
     "ventas@universalrepuestoswg.co" if i == 1 else f"contacto{i}@proveedor.co", True)
    for i, (nit, n, a) in enumerate(COMPANIES, 1)])
WAREHOUSES = [(1, "Bodega principal 7 de Agosto", "Calle 63F #25-49, Bogotá"),
              (1, "Bodega Norte", "Av. Calle 134 #19-20, Bogotá"),
              (1, "Bodega Sur", "Autopista Sur #60-30, Soacha")] + \
             [(i, f"Bodega {COMPANIES[i - 1][1]}", COMPANIES[i - 1][2]) for i in range(2, 21)]
table("company_warehouse", ["company_warehouse_id", "company_id", "name", "address", "state"],
      [(i, c, n, a, True) for i, (c, n, a) in enumerate(WAREHOUSES, 1)])

# ---------------------------------------------------------------- personas y usuarios
CLAVE_DEMO = "Repuestos#2026"
H_USER = generate_password_hash(CLAVE_DEMO)  # scrypt con sal (igual que Seguridad.contrasenas)
PEOPLE = [  # (first, second, last, second_last, username, role, city)
    ("Admin", None, "Sistema", None, "admin", "administrador", 1),
    ("Wilson", "Andrés", "Gómez", "Rojas", "wgomez", "administrador", 1),
    ("Paola", None, "Martínez", "Díaz", "pmartinez", "empacador", 1),
    ("Jhon", "Fredy", "Ramírez", "Castro", "jramirez", "empacador", 1),
    ("Luis", "Carlos", "Pardo", None, "lpardo", "empacador", 4),
    ("Diego", None, "Moreno", "Vargas", "dmoreno", "repartidor", 1),
    ("Camilo", "Esteban", "Rincón", "Lozano", "crincon", "repartidor", 1),
    ("Sergio", None, "Quintero", "Mejía", "squintero", "repartidor", 21),
    ("Yeison", "David", "Cárdenas", None, "ycardenas", "repartidor", 4),
    ("Laura", "Valentina", "Hernández", "Suárez", "lhernandez", "cliente", 1),
    ("Andrés", None, "Torres", "Peña", "atorres", "cliente", 1),
    ("María", "José", "López", "García", "mlopez", "cliente", 2),
    ("Juan", "Sebastián", "Rodríguez", "Ruiz", "jrodriguez", "cliente", 1),
    ("Carolina", None, "Sánchez", "Ortiz", "csanchez", "cliente", 3),
    ("Felipe", "Alejandro", "Castillo", "Mora", "fcastillo", "cliente", 21),
    ("Natalia", None, "Jiménez", "Reyes", "njimenez", "cliente", 1),
    ("Óscar", "Iván", "Gutiérrez", None, "ogutierrez", "cliente", 22),
    ("Daniela", None, "Muñoz", "Ríos", "dmunoz", "cliente", 5),
    ("Ricardo", None, "Álvarez", "Silva", "ralvarez", "cliente", 6),
    ("Tatiana", "Lucía", "Romero", "Cruz", "tromero", "cliente", 1),
    ("Hernán", None, "Vargas", "Pinto", "hvargas", "cliente", 9),
    ("Sofía", None, "Navarro", "Acosta", "snavarro", "cliente", 14),
    ("Taller", None, "El Pistón", "S.A.S.", "tallerpiston", "cliente", 1),
    ("Flota", None, "Transportes", "Ruta 7", "flotaruta7", "cliente", 4),
]
persons, users = [], []
start_users = datetime(2026, 1, 10, 8, 0, tzinfo=timezone(timedelta(hours=-5)))
for i, (f, s2, ap1, ap2, u, role, city) in enumerate(PEOPLE, 1):
    doc = 3 if u in ("tallerpiston", "flotaruta7") else (1 if i % 7 else 2)
    ident = "0000000000" if u == "admin" else str(1000000000 + i * 7919)
    email = "admin@repuestos.local" if u == "admin" else f"{u}@correo.co"
    bdate = None if doc == 3 else datetime(1970 + (i * 3) % 35, 1 + i % 12, 1 + (i * 5) % 28).date().isoformat()
    persons.append((i, city, doc, f, s2, ap1, ap2, bdate, ident, email, f"3{random.randint(100000000, 299999999)}"))
    users.append((i, u, email, H_USER, True, i, role, start_users + timedelta(days=i)))
table("person", ["person_id", "city_id", "document_type_id", "first_name", "second_name", "last_name",
                 "second_last_name", "birth_date", "identification", "email", "phone_number"], persons)
table("app_user", ["user_id", "username", "email", "password_hash", "status", "person_id", "role", "creado_en"], users)
CLIENTS = [u for u in users if u[6] == "cliente"]
COURIERS = [u[0] for u in users if u[6] == "repartidor"]
FULLNAME = {p[0]: f"{p[3]} {p[5]}" for p in persons}
CITYNAME = {i: n for i, (n, _) in enumerate(CITIES, 1)}

# ---------------------------------------------------------------- vehículos
CARS = [  # (name, year, brand, cc, type)
    ("Mazda 3", "2018", "Mazda", "1.6L", "sedan"), ("Mazda 2", "2019", "Mazda", "1.5L", "hatch"),
    ("Mazda CX-5", "2021", "Mazda", "2.0L", "suv"), ("Chevrolet Spark GT", "2018", "Chevrolet", "1.2L", "hatch"),
    ("Chevrolet Sail", "2019", "Chevrolet", "1.4L", "sedan"), ("Chevrolet Onix", "2022", "Chevrolet", "1.0L", "sedan"),
    ("Chevrolet Tracker", "2021", "Chevrolet", "1.2L", "cross"), ("Chevrolet Blazer", "2023", "Chevrolet", "3.6L", "suv"),
    ("Renault Logan", "2017", "Renault", "1.6L", "sedan"), ("Renault Sandero", "2019", "Renault", "1.6L", "hatch"),
    ("Renault Duster", "2020", "Renault", "1.6L", "suv"), ("Renault Duster", "2022", "Renault", "1.3L", "suv"),
    ("Toyota Corolla", "2020", "Toyota", "1.8L", "sedan"), ("Toyota Hilux", "2021", "Toyota", "2.8L", "pick"),
    ("Toyota Fortuner", "2019", "Toyota", "2.7L", "suv"), ("Hyundai i10", "2016", "Hyundai", "1.2L", "hatch"),
    ("Hyundai Accent", "2015", "Hyundai", "1.4L", "sedan"), ("Hyundai Tucson", "2020", "Hyundai", "2.0L", "suv"),
    ("Hyundai Tucson", "2017", "Hyundai", "2.0L", "suv"), ("Kia Picanto", "2019", "Kia", "1.0L", "hatch"),
    ("Kia Rio", "2020", "Kia", "1.4L", "sedan"), ("Kia Sportage", "2021", "Kia", "2.0L", "suv"),
    ("Kia Sportage", "2018", "Kia", "2.0L", "suv"), ("Nissan March", "2018", "Nissan", "1.6L", "hatch"),
    ("Nissan Versa", "2020", "Nissan", "1.6L", "sedan"), ("Nissan Frontier", "2022", "Nissan", "2.5L", "pick"),
    ("Ford Ranger", "2021", "Ford", "3.2L", "pick"), ("Volkswagen Gol", "2016", "Volkswagen", "1.6L", "hatch"),
    ("Suzuki Swift", "2020", "Suzuki", "1.2L", "hatch"), ("Mitsubishi L200", "2019", "Mitsubishi", "2.4L", "pick"),
]
table("car", ["car_id", "product_id", "name", "chassis_number", "model", "state", "cylinder_capacity_id",
              "car_brand_id", "car_type_id"],
      [(i, None, n, f"9{B[b]:02d}{y}{i:06d}CO", y, True, CC[cc], B[b], CT[t]) for i, (n, y, b, cc, t) in enumerate(CARS, 1)])
CAR_ID = {}
for i, (n, _anio, *_r) in enumerate(CARS, 1):
    CAR_ID.setdefault(n, []).append(i)


def cars(*names):
    out = []
    for n in names:
        out += CAR_ID[n]
    return sorted(out)


SEDANS = cars("Mazda 3", "Chevrolet Sail", "Renault Logan", "Toyota Corolla", "Hyundai Accent", "Kia Rio", "Nissan Versa")
SMALL = cars("Chevrolet Spark GT", "Hyundai i10", "Kia Picanto", "Chevrolet Onix", "Suzuki Swift", "Nissan March")
SUVS = cars("Mazda CX-5", "Chevrolet Tracker", "Chevrolet Blazer", "Renault Duster", "Toyota Fortuner", "Hyundai Tucson", "Kia Sportage")
PICKUPS = cars("Toyota Hilux", "Nissan Frontier", "Ford Ranger", "Mitsubishi L200")
ALL = list(range(1, len(CARS) + 1))

# ---------------------------------------------------------------- productos
PRODUCTS = [  # (nombre, descripción, precio sin IVA, categoría, marca repuesto, vehículos compatibles)
    ("Filtro de aceite", "Filtro de aceite de motor, rosca estándar", 25000, "Filtros", "Mann-Filter", cars("Mazda 3", "Mazda 2", "Mazda CX-5")),
    ("Kit de empaques de motor", "Juego completo de empaques de culata y cárter", 180000, "Motor", "Mahle", cars("Mazda 3", "Mazda 2")),
    ("Radiador Kia Sportage - Tucson", "Radiador con tanques plásticos. 6 meses de garantía (carro normal) y 3 meses (taxi)", 520000, "Radiadores", "Valeo", cars("Kia Sportage", "Hyundai Tucson")),
    ("Radiador Chevrolet Spark GT", "Radiador de aluminio, núcleo 16 mm", 310000, "Radiadores", "Denso", cars("Chevrolet Spark GT")),
    ("Radiador Renault Logan - Sandero", "Radiador mecánico con A/A", 345000, "Radiadores", "Valeo", cars("Renault Logan", "Renault Sandero")),
    ("Radiador Toyota Hilux", "Radiador reforzado para trabajo pesado", 890000, "Radiadores", "Denso", cars("Toyota Hilux")),
    ("Filtro de aire motor", "Filtro de aire de alto flujo", 38000, "Filtros", "Bosch", SEDANS),
    ("Filtro de cabina con carbón activado", "Retiene polen y olores", 42000, "Filtros", "Mann-Filter", SUVS),
    ("Filtro de combustible", "Filtro de gasolina en línea", 31000, "Filtros", "Bosch", SMALL + SEDANS),
    ("Pastillas de freno delanteras", "Pastillas cerámicas de bajo polvo", 95000, "Frenos", "Brembo", SEDANS + SMALL),
    ("Discos de freno ventilados (par)", "Discos delanteros ventilados", 260000, "Frenos", "Brembo", SUVS),
    ("Bandas de freno traseras", "Juego de bandas para campana", 78000, "Frenos", "Bosch", SMALL),
    ("Líquido de frenos DOT 4", "Botella 500 ml", 24000, "Frenos", "Bosch", ALL),
    ("Tijera de suspensión inferior", "Brazo de control con buje", 175000, "Suspensión", "Moog", SEDANS),
    ("Terminal de dirección", "Terminal exterior con tuerca", 58000, "Dirección", "Moog", SMALL + SEDANS),
    ("Rótula de suspensión", "Rótula inferior reforzada", 69000, "Suspensión", "Moog", SUVS + PICKUPS),
    ("Amortiguador delantero a gas", "Amortiguador hidráulico presurizado", 210000, "Amortiguadores", "Monroe", SEDANS),
    ("Amortiguador trasero SUV", "Amortiguador para carga media", 235000, "Amortiguadores", "Monroe", SUVS),
    ("Amortiguador pickup trabajo pesado", "Alta capacidad de carga", 280000, "Amortiguadores", "Sachs", PICKUPS),
    ("Kit de embrague completo", "Disco, prensa y balinera", 620000, "Embrague", "Luk", SEDANS),
    ("Kit de embrague pickup", "Kit reforzado para diésel", 980000, "Embrague", "Sachs", PICKUPS),
    ("Bujías de iridio (x4)", "Juego de 4 bujías de larga duración", 128000, "Encendido", "NGK", SMALL + SEDANS),
    ("Bobina de encendido", "Bobina tipo lápiz", 155000, "Encendido", "Delphi", SEDANS + SUVS),
    ("Cables de alta tensión", "Juego de cables de bujía", 89000, "Encendido", "NGK", SMALL),
    ("Bombillo H4 halógeno (par)", "Luz blanca 60/55 W", 46000, "Iluminación", "Philips", ALL),
    ("Farola delantera derecha", "Farola completa con base", 390000, "Iluminación", "Hella", cars("Chevrolet Onix", "Chevrolet Tracker")),
    ("Kit LED H7", "6000K, 2 unidades", 120000, "Iluminación", "Philips", SEDANS + SUVS),
    ("Batería 12V 45Ah", "Batería libre de mantenimiento", 365000, "Baterías", "Bosch", SMALL),
    ("Batería 12V 60Ah", "Batería sellada para sedán y SUV", 455000, "Baterías", "Bosch", SEDANS + SUVS),
    ("Batería 12V 90Ah diésel", "Alto arranque en frío", 690000, "Baterías", "Bosch", PICKUPS),
    ("Correa de repartición", "Correa dentada con 2 tensores", 210000, "Correas", "Gates", SEDANS + SMALL),
    ("Correa de accesorios", "Correa poly-V", 65000, "Correas", "Gates", ALL),
    ("Bomba de agua", "Bomba con empaque", 185000, "Bombas de agua", "Gates", SEDANS + SMALL),
    ("Bomba de agua SUV", "Bomba con polea", 245000, "Bombas de agua", "Koyo", SUVS),
    ("Silenciador trasero", "Silenciador en acero aluminizado", 230000, "Escape", "Genérica", SEDANS),
    ("Catalizador universal", "Catalizador de 2 pulgadas", 540000, "Escape", "Genérica", ALL),
    ("Caja de dirección hidráulica", "Remanufacturada con garantía", 1150000, "Dirección", "Moog", cars("Renault Logan", "Renault Sandero", "Renault Duster")),
    ("Aceite de caja ATF (1 L)", "Fluido para transmisión automática", 48000, "Transmisión", "Mobil", ALL),
    ("Kit de rodamientos de caja", "Rodamientos de caja manual", 330000, "Transmisión", "SKF", SEDANS),
    ("Bómper delantero", "Bómper en polipropileno para pintar", 420000, "Carrocería", "Genérica", cars("Chevrolet Spark GT", "Kia Picanto")),
    ("Guardafango delantero izquierdo", "Lámina original", 260000, "Carrocería", "Genérica", cars("Renault Sandero", "Renault Logan")),
    ("Espejo retrovisor derecho eléctrico", "Con direccional", 285000, "Espejos", "Valeo", SUVS),
    ("Luna de espejo con desempañador", "Vidrio de repuesto", 72000, "Espejos", "Genérica", ALL),
    ("Rodamiento de rueda delantero", "Balinera con sensor ABS", 145000, "Rodamientos", "SKF", SEDANS + SUVS),
    ("Rodamiento trasero", "Balinera cónica", 98000, "Rodamientos", "Koyo", SMALL),
    ("Sensor de oxígeno", "Sonda lambda de 4 cables", 230000, "Sensores", "Bosch", SEDANS + SUVS),
    ("Sensor de temperatura", "Bulbo de temperatura de motor", 55000, "Sensores", "Delphi", ALL),
    ("Aceite 10W-30 sintético (4 L)", "Galón de aceite sintético", 165000, "Lubricantes", "Mobil", SEDANS + SMALL),
    ("Aceite 15W-40 diésel (4 L)", "Para motores diésel", 175000, "Lubricantes", "Castrol", PICKUPS),
    ("Refrigerante listo para usar (1 gal)", "Anticongelante color verde", 45000, "Lubricantes", "Castrol", ALL),
]
products, spare_parts, inventory = [], [], []
for i, (n, d, price, cat, pb, comp) in enumerate(PRODUCTS, 1):
    products.append((i, n, d, Decimal(price), True, comp, i))
    spare_parts.append((i, i, n, True, T[cat], PB[pb]))
    reorder = random.choice([5, 8, 10])
    qty = random.choice([0, 3, 4]) if i % 9 == 0 else random.randint(12, 90)
    inventory.append((len(inventory) + 1, i, 1, qty, 3, 120, reorder))
    if i % 2 == 0:
        inventory.append((len(inventory) + 1, i, 2, random.randint(5, 40), 2, 60, 5))
table("product", ["product_id", "name", "description", "unit_price", "state", "fk_car_product", "fk_spare_part"], products)
table("spare_part", ["spare_part_id", "product_id", "name", "state", "spare_part_type_id", "spare_part_brand_id"], spare_parts)
table("inventory", ["inventory_id", "product_id", "company_warehouse_id", "quantity_available", "minimum_stock",
                    "maximum_stock", "reorder_stock"], inventory)

# ---------------------------------------------------------------- ventas
STATE_ID = {"Pendiente": 1, "Pagada": 2, "Despachada": 3, "Entregada": 4, "Cancelada": 5}
PLAN = ["Entregada"] * 14 + ["Despachada"] * 6 + ["Pagada"] * 6 + ["Pendiente"] * 4 + ["Cancelada"] * 2
random.shuffle(PLAN)  # reparte los estados a lo largo de los meses
METHODS = ["tarjeta_credito", "tarjeta_debito", "pse", "transferencia", "nequi", "efectivo"]
STREETS = ["Calle 63F #25-49", "Carrera 24 #64-10", "Calle 72 #11-30", "Carrera 15 #93-60", "Calle 26 #68-35",
           "Avenida Boyacá #45-20", "Carrera 7 #45-12", "Calle 13 #50-25", "Transversal 60 #128-40", "Calle 80 #69-70"]
start = datetime(2026, 5, 4, 9, 0, tzinfo=timezone(timedelta(hours=-5)))
sales, details, payments, deliveries, invoices, inv_details = [], [], [], [], [], []
for sid, state in enumerate(PLAN, 1):
    client = CLIENTS[(sid * 5) % len(CLIENTS)]
    uid = client[0]
    date = start + timedelta(days=int((sid - 1) * 5.8), hours=random.randint(0, 9), minutes=random.randint(0, 59))
    if state in ("Pendiente", "Pagada"):
        date = datetime(2026, 11, 3, 10, tzinfo=date.tzinfo) + timedelta(days=sid % 12, hours=sid % 7)
    picks = random.sample(range(1, len(PRODUCTS) + 1), random.randint(1, 4))
    subtotal, lines = Decimal(0), []
    for pid in picks:
        qty = random.randint(1, 3)
        price = products[pid - 1][3]
        disc = money(price * qty * Decimal("0.05")) if sid % 6 == 0 else Decimal("0.00")
        line = money(price * qty - disc)
        subtotal += line
        lines.append((pid, qty, price, disc, line))
        details.append((len(details) + 1, sid, pid, qty, money(price), disc, line))
    subtotal = money(subtotal)
    tax = money(subtotal * IVA)
    total = subtotal + tax
    stype = 1 if sid % 5 else random.choice([2, 4, 5])
    sales.append((sid, uid, stype, STATE_ID[state], 1, FULLNAME[uid], "Entregar en portería" if sid % 4 == 0 else None,
                  date, subtotal, tax, total))
    city = CITYNAME[persons[uid - 1][1]]
    address = f"{STREETS[sid % len(STREETS)]}, {city}"
    if state == "Cancelada":
        deliveries.append((len(deliveries) + 1, sid, address, None, None, "cancelado", None))
        continue
    if state == "Pendiente":
        deliveries.append((len(deliveries) + 1, sid, address, None, None, "pendiente", None))
        continue
    method = METHODS[sid % len(METHODS)]
    pdate = date + timedelta(minutes=random.randint(3, 40))
    ref = f"PAY{sid:04d}{random.randint(100000, 999999)}"
    if method.startswith("tarjeta"):
        ref += f"-****{random.randint(1000, 9999)}"
    payments.append((len(payments) + 1, sid, pdate, total, method, ref, "aprobado", True))
    guide = f"GUIA-{sid:04d}{random.randint(100000, 999999)}"
    courier = COURIERS[sid % len(COURIERS)]
    if state == "Pagada":
        status = "empacado" if sid % 2 else "pendiente"
        deliveries.append((len(deliveries) + 1, sid, address, None, guide if status == "empacado" else None, status,
                           courier if status == "empacado" else None))
    elif state == "Despachada":
        deliveries.append((len(deliveries) + 1, sid, address, None, guide, "en_camino", courier))
    else:
        deliveries.append((len(deliveries) + 1, sid, address, pdate + timedelta(days=random.randint(1, 3)), guide,
                           "entregado", courier))
    # factura electrónica para ventas pagadas/despachadas/entregadas
    iid = len(invoices) + 1
    number = f"FE-{sid:08d}"
    idate = pdate + timedelta(hours=2)
    invoices.append((iid, sid, number, idate, subtotal, tax, total,
                     f"FACTURA:{number}|NIT:{COMPANIES[0][0]}|FECHA:{idate:%Y-%m-%d}|IVA:{tax}|TOTAL:{total}",
                     None, None, "emitida"))
    for pid, qty, price, disc, line in lines:
        inv_details.append((len(inv_details) + 1, iid, pid, qty, money(price), disc, money(line * IVA), line))

table("sale", ["sale_id", "user_id", "sale_type_id", "sale_state_id", "company_warehouse_id", "customer_name",
               "description", "sale_date", "subtotal", "tax", "total"], sales)
table("sale_detail", ["sale_detail_id", "sale_id", "product_id", "quantity", "unit_price", "discount", "subtotal"], details)
table("payment", ["payment_id", "sale_id", "payment_date", "amount", "method", "reference", "status", "receipt_issued"], payments)
table("delivery", ["delivery_id", "sale_id", "address", "delivery_date", "tracking_number", "status", "assigned_user_id"], deliveries)
table("electronic_invoice", ["invoice_id", "sale_id", "invoice_number", "issue_date", "subtotal", "tax", "total",
                             "qr_code", "pdf_path", "xml_path", "status"], invoices)
table("invoice_detail", ["invoice_detail_id", "invoice_id", "product_id", "quantity", "unit_price", "discount", "tax",
                         "subtotal"], inv_details)


# ---------------------------------------------------------------- seguridad: sesiones históricas y auditoría
STAFF_IDS = [u[0] for u in users if u[6] != "cliente"]
sesiones, auditoria = [], []
for k in range(24):
    uid = (STAFF_IDS + [c[0] for c in CLIENTS])[k % (len(STAFF_IDS) + len(CLIENTS))]
    emit = start + timedelta(days=k * 7, hours=k % 9)
    revocada = k % 3 != 0
    sesiones.append((f"{k:02d}" + f"{random.getrandbits(120):030x}", uid, emit, emit + timedelta(hours=2),
                     f"190.24.{k}.{10 + k}", f"{random.getrandbits(256):064x}",
                     emit + timedelta(minutes=40) if revocada else None, "LOGOUT" if revocada else None))
    auditoria.append((len(auditoria) + 1, uid, users[uid - 1][1], "LOGIN", "usuario", f"sesion={sesiones[-1][0][:8]}",
                      f"190.24.{k}.{10 + k}", emit))
for sid, uid, *_r in sales[:20]:
    auditoria.append((len(auditoria) + 1, uid, users[uid - 1][1], "CREAR", "venta", f"sale_id={sid}", None, _r[5]))
table("sesion_jwt", ["jti", "user_id", "emitido_en", "expira_en", "ip", "agente_hash", "revocado_en", "motivo_revocacion"], sesiones)
table("auditoria", ["id_auditoria", "user_id", "username", "accion", "entidad", "detalle", "ip", "fecha"], auditoria)


# ---------------------------------------------------------------- salida
def main():
    out = ["-- Datos de prueba generados por database/generar_datos.py (no editar a mano)",
           "-- Contraseña de todos los usuarios de ejemplo: Repuestos#2026", ""]
    for name, cols, rows in TABLES:
        if len(rows) < 20:
            raise SystemExit(f"{name} tiene {len(rows)} registros (mínimo 20)")
        out.append(f"-- {name}: {len(rows)} registros")
        out.append(f"INSERT INTO automotriz.{name} ({', '.join(cols)}) VALUES")
        out.append(",\n".join("  (" + ", ".join(q(v) for v in r) + ")" for r in rows)
                   + (" ON CONFLICT DO NOTHING;" if name in SIN_CONFLICTO else ";"))
        pk = cols[0]
        if name != "sesion_jwt":
            # nombres de tabla/columna fijos del propio generador (no hay entrada de usuario)
            out.append(f"SELECT setval(pg_get_serial_sequence('automotriz.{name}', '{pk}'), "  # noqa: S608
                       f"(SELECT MAX({pk}) FROM automotriz.{name}));")
        out.append("")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    for name, _, rows in TABLES:
        print(f"{name:20s} {len(rows)}")


if __name__ == "__main__":
    main()
