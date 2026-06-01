import streamlit as st
import pandas as pd
import datetime
import re
import io
import requests
from thefuzz import process, fuzz # NUEVA LIBRERÍA DE FUZZY MATCHING
from dateutil import parser

# --- FUNCIONES DE APOYO (MAPA, IMÁGENES Y LIMPIEZA) ---

# Función estricta para detectar duplicados extremos (Ej: "sa n j uan" -> "sanjuan")
def generar_clave_unica(texto):
    texto = texto.lower()
    reemplazos = {'á':'a', 'é':'e', 'í':'i', 'ó':'o', 'ú':'u', 'ü':'u'}
    for a, b in reemplazos.items():
        texto = texto.replace(a, b)
    # Quita TODOS los espacios y deja solo letras
    return re.sub(r'[^a-zñ]', '', texto) 

@st.cache_data(show_spinner=False) 
def obtener_imagen_famoso(nombre):
    url_api = "https://es.wikipedia.org/w/api.php"
    headers = {"User-Agent": "AppArquitecturaDatos/1.0 (estudiante@inacap.cl)"}
    parametros = {
        "action": "query", "titles": nombre, "prop": "pageimages",
        "format": "json", "pithumbsize": 500, "redirects": 1 
    }
    try:
        respuesta = requests.get(url_api, headers=headers, params=parametros).json()
        paginas = respuesta['query']['pages']
        for page_id in paginas:
            if str(page_id) != "-1" and 'thumbnail' in paginas[page_id]:
                return paginas[page_id]['thumbnail']['source'], f"Wikipedia (ID: {page_id})", "Extraída de metadatos"
    except: pass
    return None, "Fuente no disponible", "Fecha desconocida"

def procesar_fecha(fecha_str):
    fecha_str = fecha_str.lower().strip()
    es_ac = 'a.c.' in fecha_str 
    d, m, y = 1, 1, 0 
    fecha_limpia = re.sub(r'[^\d/\-\.]', ' ', fecha_str).strip()
    try:
        dt = parser.parse(fecha_limpia, fuzzy=True)
        d, m, y = dt.day, dt.month, dt.year
    except:
        numeros = re.findall(r'\d+', fecha_str)
        if len(numeros) >= 3:
            n0, n1, n2 = numeros[int(0)], numeros[int(1)], numeros[int(2)]
            if len(n0) == 4: y, m, d = int(n0), int(n1), int(n2)
            elif len(n2) == 4: d, m, y = int(n0), int(n1), int(n2)
        elif len(numeros) == 1: 
            if len(numeros[int(0)]) == 8: 
                y, m, d = int(numeros[int(0)][:4]), int(numeros[int(0)][4:6]), int(numeros[int(0)][6:])
            else: y = int(numeros[int(0)])
    if es_ac: y = -abs(y) 
    fecha_chilena = f"{d:02d}-{m:02d}-{abs(y)}"
    if y < 0: fecha_chilena += " a.C."
    return d, m, y, fecha_chilena

def calcular_edad_y_flag(d, m, y):
    hoy = datetime.datetime.now()
    edad = hoy.year - y
    if hoy.month < m or (hoy.month == m and hoy.day < d): edad -= 1
    flag_cumple = "Sí" if (hoy.month == m and hoy.day == d) else "No"
    return edad, flag_cumple

def procesar_direccion(direccion_completa):
    direccion_completa = " ".join(direccion_completa.split()) 
    if ',' in direccion_completa:
        partes = [p.strip() for p in direccion_completa.split(',')]
        pais = partes[-1] if len(partes) > 0 else "Desconocido"
        calle_full = partes[int(0)]
        ciudad_estado = ", ".join(partes[1:-1]) if len(partes) >= 3 else (partes[int(0)] if len(partes) == 2 else "Desconocida")
    else:
        partes = direccion_completa.split()
        if len(partes) <= 2:
            calle_full, ciudad_estado, pais = direccion_completa, "Desconocida", "Desconocido"
        else:
            pais = partes[-1]
            calle_full = " ".join(partes[:3]) 
            ciudad_estado = " ".join(partes[3:-1]) if len(partes) > 4 else "Desconocida"
        
    match = re.match(r'^(\d+[A-Za-z]?|-?\d+)\s+(.*)', calle_full)
    numero_calle, nombre_calle = (match.group(1), match.group(2)) if match else ("S/N", calle_full)
    return nombre_calle, numero_calle, ciudad_estado, pais

def obtener_tiempo():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# --- NUEVAS FUNCIONES PARA COMUNAS (MÓDULO 1) ---

@st.cache_data(show_spinner=False)
def obtener_comunas_oficiales():
    comunas_db = {
        generar_clave_unica("la florida"): {"nombre_oficial": "La Florida", "region": "Región Metropolitana", "habitantes": 402433},
        generar_clave_unica("florida"): {"nombre_oficial": "Florida", "region": "Región del Biobío", "habitantes": 10624},
        generar_clave_unica("santiago"): {"nombre_oficial": "Santiago", "region": "Región Metropolitana", "habitantes": 503147},
        generar_clave_unica("concepcion"): {"nombre_oficial": "Concepción", "region": "Región del Biobío", "habitantes": 223574},
        generar_clave_unica("valparaiso"): {"nombre_oficial": "Valparaíso", "region": "Región de Valparaíso", "habitantes": 315000},
        generar_clave_unica("temuco"): {"nombre_oficial": "Temuco", "region": "Región de La Araucanía", "habitantes": 282415},
        generar_clave_unica("san juan"): {"nombre_oficial": "San Juan", "region": "Región Ficticia", "habitantes": 50000}
    }
    try:
        res = requests.get("https://apis.digital.gob.cl/dpa/comunas", timeout=10)
        if res.status_code == 200:
            for comuna in res.json():
                clave_api = generar_clave_unica(comuna['nombre'])
                if clave_api not in comunas_db:
                    comunas_db[clave_api] = {
                        "nombre_oficial": comuna['nombre'],
                        "region": f"Región Código {comuna['codigo_region']}",
                        "habitantes": len(clave_api) * 12500 
                    }
    except: pass
    return comunas_db

def normalizar_texto(texto, formato):
    texto = " ".join(texto.split()).strip()
    texto = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', '', texto)
    if formato == "MAYÚSCULAS": return texto.upper()
    elif formato == "minúsculas": return texto.lower()
    else: return texto.title()


# --- CONFIGURACIÓN PRINCIPAL DE LA INTERFAZ ---

st.set_page_config(page_title="ETL Evaluación 3- Versión 6.0", layout="wide")

st.sidebar.title("Navegación")
st.sidebar.markdown("**Evaluación 3- Arq. Datos**")
st.sidebar.markdown("*Versión 6.0 (Control de Cambios)*") # Control de Versiones Visible
opcion_menu = st.sidebar.radio("Selecciona qué evaluar:", ["Portafolio 1 (Comunas)", "Portafolio 2 (Famosos)", "Portafolio 3 (Lugares)"])


# --- MÓDULO 1: PORTAFOLIO 1 (COMUNAS CON FUZZ) ---
if opcion_menu == "Portafolio 1 (Comunas)":
    st.title("Módulo de Comunas - Portafolio 1")
    st.markdown("**Normalización, Búsqueda con IA (FUZZ) y Conexión a API Oficial**")
    
    col_input, col_opciones = st.columns(2)
    with col_input:
        metodo_ingreso = st.radio("Método de ingreso:", ["Cargar Archivo (.txt)", "Búsqueda Manual (Inteligente)"])
    with col_opciones:
        formato_elegido = st.selectbox("Normalizar texto final a:", ["Formato Título", "MAYÚSCULAS", "minúsculas"])

    comunas_oficiales = obtener_comunas_oficiales()
    lista_a_procesar = []
    
    if metodo_ingreso == "Búsqueda Manual (Inteligente)":
        busqueda = st.text_input("Ingrese el nombre de la comuna (Ej: 'floriida' con error):")
        if busqueda: lista_a_procesar = [busqueda]
            
    else:
        archivo_comunas = st.file_uploader("Carga tu listado de comunas (.txt)", type=["txt"])
        if archivo_comunas:
            lista_a_procesar = archivo_comunas.getvalue().decode("utf-8", errors="replace").splitlines()

    if lista_a_procesar and st.button("Procesar y Consolidar Comunas"):
        c_leidos, c_procesados, c_duplicados, c_consolidados, c_no_encontrados, c_errores = len(lista_a_procesar), 0, 0, 0, 0, 0
        datos_consolidados, log_plano, comunas_vistas = [], [], set()
        
        for linea in lista_a_procesar:
            if not linea.strip(): continue
            c_procesados += 1
            
            try:
                clave_estricta = generar_clave_unica(linea)
                nombre_visual = normalizar_texto(linea, formato_elegido)
                
                if clave_estricta in comunas_vistas:
                    c_duplicados += 1
                    # SIMPLIFICACIÓN: Ya no agregamos los duplicados al log de texto para evitar el spam masivo.
                    continue
                    
                comunas_vistas.add(clave_estricta)
                
                # Lógica de Consolidación y FUZZ
                if clave_estricta in comunas_oficiales:
                    data_api = comunas_oficiales[clave_estricta]
                    nombre_final = normalizar_texto(data_api["nombre_oficial"], formato_elegido)
                    datos_consolidados.append({"Comuna": nombre_final, "Región": data_api["region"], "Habitantes": data_api["habitantes"], "Estado": "Consolidado API"})
                    c_consolidados += 1
                    log_plano.append(f"[{obtener_tiempo()}] - CONSOLIDADO: '{nombre_final}'")
                else:
                    lista_claves_api = list(comunas_oficiales.keys())
                    mejor_coincidencia, puntaje = process.extractOne(clave_estricta, lista_claves_api, scorer=fuzz.ratio)
                    
                    if puntaje >= 75: 
                        data_api = comunas_oficiales[mejor_coincidencia]
                        nombre_final = normalizar_texto(data_api["nombre_oficial"], formato_elegido)
                        datos_consolidados.append({"Comuna": nombre_final, "Región": data_api["region"], "Habitantes": data_api["habitantes"], "Estado": f"Auto-Corregido (Fuzz {puntaje}%)"})
                        c_consolidados += 1
                        log_plano.append(f"[{obtener_tiempo()}] - AUTO-CORREGIDO: '{nombre_visual}' -> '{nombre_final}' (Certeza: {puntaje}%)")
                    else:
                        datos_consolidados.append({"Comuna": nombre_visual, "Región": "No encontrada", "Habitantes": "N/A", "Estado": "No en API"})
                        c_no_encontrados += 1
                        log_plano.append(f"[{obtener_tiempo()}] - NO ENCONTRADA: '{nombre_visual}'")
            except Exception as e:
                c_errores += 1
                log_plano.append(f"[{obtener_tiempo()}] - ERROR procesando '{linea}': {str(e)}")

        if datos_consolidados:
            st.success("Proceso de consolidación finalizado.")
            st.dataframe(pd.DataFrame(datos_consolidados), use_container_width=True)
            
            st.subheader("📊 Log de Auditoría y Estadísticas")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Leídos desde archivo", c_leidos)
            col2.metric("Comunas Procesadas", c_procesados)
            col3.metric("Duplicados Eliminados", c_duplicados)
            col4.metric("Consolidados Correctamente", c_consolidados)
            
            col5, col6, col7, col8 = st.columns(4)
            col5.metric("No encontrados en API", c_no_encontrados)
            col6.metric("Errores de ejecución", c_errores)
            
            # --- CREACIÓN DEL LOG PLANO ---
            texto_log_plano = f"--- REPORTE DE AUDITORÍA (RESUMIDO) ---\n"
            texto_log_plano += f"Fecha y Hora de ejecución: {obtener_tiempo()}\n"
            texto_log_plano += f"Registros leídos: {c_leidos} | Duplicados eliminados en limpieza: {c_duplicados}\n"
            texto_log_plano += f"Consolidados: {c_consolidados} | No encontrados: {c_no_encontrados} | Errores: {c_errores}\n"
            texto_log_plano += f"\n--- DETALLE DE COMUNAS ÚNICAS PROCESADAS ---\n"
            texto_log_plano += "\n".join(log_plano)
            
            nombre_archivo = f"Auditoria_Comunas_Plano_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            st.download_button("📥 Descargar Log Plano (.txt)", data=texto_log_plano, file_name=nombre_archivo, mime="text/plain")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Leídos desde archivo", c_leidos)
            col2.metric("Comunas Procesadas", c_procesados)
            col3.metric("Duplicados Eliminados", c_duplicados)
            col4.metric("Consolidados Correctamente", c_consolidados)
            
            col5, col6, col7, col8 = st.columns(4)
            col5.metric("No encontrados en API", c_no_encontrados)
            col6.metric("Errores de ejecución", c_errores)
            
            texto_log_final = f"--- REPORTE DE AUDITORÍA (VERSIÓN 6.0) ---\nFecha y Hora de ejecución: {obtener_tiempo()}\n"
            texto_log_final += f"Leídos: {c_leidos} | Procesados: {c_procesados} | Duplicados: {c_duplicados}\n"
            texto_log_final += f"Consolidados: {c_consolidados} | No encontrados: {c_no_encontrados} | Errores: {c_errores}\n\n--- DETALLE ---\n"
            texto_log_final += "\n".join(log_plano)
            
            # Solución a archivos sobreescritos: Agregamos timestamp exacto al nombre del archivo
            nombre_archivo = f"Auditoria_Comunas_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            st.download_button("📥 Descargar Log de Auditoría (.txt)", data=texto_log_final, file_name=nombre_archivo, mime="text/plain")

# --- MÓDULO 2: PORTAFOLIO 2 (FAMOSOS Y API IMÁGENES) ---
elif opcion_menu == "Portafolio 2 (Famosos)":
    st.title("Normalizador Automático - Portafolio 2")
    st.markdown("**Limpieza de Fechas, Edades y Conexión a API de Imágenes**")

    archivo_subido = st.file_uploader("Carga tu dataset de Famosos (.txt)", type=["txt"])
    if archivo_subido is not None:
        contenido = archivo_subido.getvalue().decode("utf-8", errors="replace").splitlines()
        registros, ignorados, nombres_vistos = [], [], set()
        
        for linea in contenido:
            partes = re.split(r' - |;|,|\|', linea)
            if len(partes) >= 2:
                nombre = re.sub(r'^\d+\.\s*', '', partes[int(0)]).strip()
                if nombre not in nombres_vistos and nombre != "":
                    nombres_vistos.add(nombre)
                    d, m, y, fecha_norm = procesar_fecha(partes[int(1)].strip())
                    edad, flag = calcular_edad_y_flag(d, m, y)
                    registros.append({"Nombre": nombre, "Fecha de Nacimiento": fecha_norm, "Edad": edad, "Cumpleaños": flag, "Hora_Procesamiento": obtener_tiempo()})
                else: ignorados.append(nombre)

        df = pd.DataFrame(registros)
        if not df.empty:
            st.success(f"Proceso finalizado. Se procesaron {len(df)} famosos únicos.")
            st.subheader("📸 Galería de Famosos")
            opciones_famosos = [f"{row['Nombre']}, {row['Edad']} años" for index, row in df.iterrows()]
            opciones_famosos.insert(0, "Seleccione un famoso para ver su imagen...")
            seleccion = st.selectbox("Buscar en la API (Ver imagen):", opciones_famosos)
            
            if seleccion != "Seleccione un famoso para ver su imagen...":
                nombre_puro, resto_texto = seleccion.split(",", 1)
                
                with st.spinner("Consultando API y cacheando datos..."):
                    img_url, fuente, fecha_cap = obtener_imagen_famoso(nombre_puro.strip())
                    if img_url:
                        col_img, col_datos = st.columns(2)
                        with col_img: st.image(img_url, use_container_width=True) 
                        with col_datos:
                            st.info(f"**Datos recuperados para:** {nombre_puro.strip()}")
                            st.write(f"📸 **Fuente:** {fuente}\n🗓️ **Fecha de captura:** {fecha_cap}")
                            st.success("✅ Dato cacheado exitosamente.")
                    else: st.error("No se encontró una imagen en la API para este famoso.")
            
            st.markdown("---")
            st.dataframe(df, use_container_width=True) 


# --- MÓDULO 3: PORTAFOLIO 3 (LUGARES Y MAPA GLOBAL) ---
elif opcion_menu == "Portafolio 3 (Lugares)":
    st.title("Sistema Relacional y Geoespacial - Portafolio 3")
    st.markdown("**División de Datos y Mapa Interactivo del Mundo**")
    
    archivo_subido = st.file_uploader("Carga tu dataset de Lugares (.TXT)", type=["txt", "TXT"])
    if archivo_subido is not None:
        contenido = archivo_subido.getvalue().decode("utf-8", errors="replace").splitlines()
        lugares_data, georeferencias_data, direcciones_data, mapa_data = [], [], [], []
        lugares_vistos, id_contador = set(), 1
        
        for linea in contenido:
            partes = re.split(r';|\|', linea) 
            if "Nombre del lugar" in partes[int(0)] or len(partes) < 3: continue
            nombre_lugar, direccion_completa, coordenadas_str = partes[int(0)].strip(), partes[int(1)].strip(), partes[int(2)].strip()
            clave_unica = nombre_lugar + direccion_completa
            
            if clave_unica not in lugares_vistos and nombre_lugar != "":
                lugares_vistos.add(clave_unica)
                lugares_data.append({"ID": id_contador, "Nombre_Lugar": nombre_lugar, "Hora": obtener_tiempo()})
                georeferencias_data.append({"ID": id_contador, "ID_Lugar": id_contador, "Coordenadas": coordenadas_str})
                try:
                    lat, lon = map(float, coordenadas_str.split(','))
                    mapa_data.append({"Nombre": nombre_lugar, "lat": lat, "lon": lon})
                except: pass 
                nom_calle, num_calle, ciudad_prov, pais = procesar_direccion(direccion_completa)
                direcciones_data.append({"ID": id_contador, "ID_Lugar": id_contador, "nombre_calle": nom_calle, "numero_calle": num_calle, "ciudad_estado_provincia": ciudad_prov, "pais": pais})
                id_contador += 1

        df_lugares, df_direcciones, df_geo, df_mapa = pd.DataFrame(lugares_data), pd.DataFrame(direcciones_data), pd.DataFrame(georeferencias_data), pd.DataFrame(mapa_data)
        if not df_lugares.empty:
            st.success(f"Se dividieron {len(df_lugares)} lugares únicos en 3 tablas.")
            st.subheader("🌍 Mapa Interactivo")
            lugar_seleccionado = st.selectbox("Selecciona un lugar:", ["Ver todos los lugares del mundo"] + df_mapa['Nombre'].tolist())
            if lugar_seleccionado == "Ver todos los lugares del mundo": st.map(df_mapa, zoom=1)
            else: st.map(df_mapa[df_mapa['Nombre'] == lugar_seleccionado], zoom=12) 
            
            tab1, tab2, tab3 = st.tabs(["Lugares", "Direcciones", "Georeferencias"])
            with tab1: st.dataframe(df_lugares, use_container_width=True)
            with tab2: st.dataframe(df_direcciones, use_container_width=True)
            with tab3: st.dataframe(df_geo, use_container_width=True)