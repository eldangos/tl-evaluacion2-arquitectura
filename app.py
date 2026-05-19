import streamlit as st
import pandas as pd
import datetime
import re
import io

# ==============================================================================
# FUNCIONES PORTAFOLIO 2 (FAMOSOS)
# ==============================================================================
def procesar_fecha(fecha_str):
    fecha_str = fecha_str.lower().strip()
    es_ac = 'a.c.' in fecha_str 
    numeros = re.findall(r'\d+', fecha_str)
    d, m, y = 1, 1, 0 
    
    if len(numeros) == 3:
        n0 = numeros[int(0)]
        n1 = numeros[int(1)]
        n2 = numeros[int(2)]
        if len(n0) == 4: 
            y, m, d = int(n0), int(n1), int(n2)
        elif len(n2) == 4: 
            d, m, y = int(n0), int(n1), int(n2)
    elif len(numeros) == 1: 
        y = int(numeros[int(0)])
            
    if es_ac: y = -y 
        
    fecha_chilena = f"{d:02d}-{m:02d}-{abs(y)}"
    if y < 0: fecha_chilena += " a.C."
    return d, m, y, fecha_chilena

def calcular_edad_y_flag(d, m, y):
    hoy = datetime.datetime.now()
    edad = hoy.year - y
    if hoy.month < m or (hoy.month == m and hoy.day < d):
        edad -= 1
    flag_cumple = "🎉 Sí" if (hoy.month == m and hoy.day == d) else "No"
    return edad, flag_cumple

# ==============================================================================
# FUNCIONES PORTAFOLIO 3 (LUGARES Y 3 TABLAS)
# ==============================================================================
def procesar_direccion(direccion_completa):
    partes = [p.strip() for p in direccion_completa.split(',')]
    pais = partes[-1] if len(partes) > 0 else "Desconocido"
    
    if len(partes) >= 3:
        ciudad_estado = ", ".join(partes[1:-1])
        calle_full = partes[int(0)]
    elif len(partes) == 2:
        ciudad_estado = partes[int(0)]
        calle_full = "Desconocida"
    else:
        ciudad_estado = partes[int(0)] if len(partes)>0 else "Desconocida"
        calle_full = "Desconocida"
        
    numero_calle = "S/N"
    nombre_calle = calle_full
    
    match = re.match(r'^(\d+[A-Za-z]?|-?\d+)\s+(.*)', calle_full)
    if match:
        numero_calle = match.group(1) 
        nombre_calle = match.group(2) 
        
    return nombre_calle, numero_calle, ciudad_estado, pais

# ==============================================================================
# INTERFAZ WEB PRINCIPAL (STREAMLIT)
# ==============================================================================
st.set_page_config(page_title="ETL Evaluación 2 - Versión 2.0", layout="wide")

st.sidebar.title("Navegación")
st.sidebar.markdown("Evaluación 2 - Arq. Datos")
opcion_menu = st.sidebar.radio("Selecciona qué evaluar:", ["Portafolio 2 (Famosos)", "Portafolio 3 (Lugares)"])

def obtener_tiempo():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# ------------------------------------------------------------------------------
# PÁGINA: PORTAFOLIO 2
# ------------------------------------------------------------------------------
if opcion_menu == "Portafolio 2 (Famosos)":
    st.title("Normalizador Automático - Portafolio 2")
    st.markdown("**Limpieza de Fechas, Edades y Cumpleaños**")

    archivo_subido = st.file_uploader("Carga tu dataset de Famosos (.txt)", type=["txt"])

    if archivo_subido is not None:
        contenido = archivo_subido.getvalue().decode("utf-8", errors="replace").splitlines()
        
        # === VALIDADOR DE ARCHIVO ESTRICTO ===
        # Exige que las líneas tengan el separador " - "
        es_archivo_correcto = any(" - " in linea for linea in contenido[:15])
        
        if not es_archivo_correcto:
            st.error("❌ **¡Archivo Incorrecto o Sin Formato!** El archivo que subiste no corresponde a los Famosos.")
            st.info("💡 Por favor, sube un archivo válido que separe el nombre de la fecha con un guion (ej: DATOS2026-2.txt).")
        else:
            registros, log_text, nombres_vistos = [], [], set()
            log_text.append(f"[{obtener_tiempo()}] - INICIO: Procesando Famosos.")
            
            for linea in contenido:
                if " - " in linea:
                    partes = linea.split(" - ")
                    if len(partes) >= 2:
                        nombre_crudo = partes[int(0)]
                        nombre = re.sub(r'^\d+\.\s*', '', nombre_crudo).strip()
                        fecha_cruda = partes[int(1)].strip()
                        
                        if nombre not in nombres_vistos:
                            nombres_vistos.add(nombre)
                            d, m, y, fecha_norm = procesar_fecha(fecha_cruda)
                            edad, flag = calcular_edad_y_flag(d, m, y)
                            
                            registros.append({
                                "Nombre": nombre, 
                                "Fecha de Nacimiento": fecha_norm, 
                                "Edad": edad, 
                                "Cumpleaños": flag,
                                "Hora_Procesamiento": obtener_tiempo()
                            })
                            log_text.append(f"[{obtener_tiempo()}] - Transformado: {nombre} | {fecha_norm}")
                        else:
                            log_text.append(f"[{obtener_tiempo()}] - Ignorado (Duplicado): {nombre}")

            log_text.append(f"[{obtener_tiempo()}] - FIN: {len(registros)} famosos procesados.")
            
            st.success(f"¡Listo! Se procesaron {len(registros)} famosos únicos.")
            df = pd.DataFrame(registros)
            st.dataframe(df, use_container_width=True) 
            
            col1, col2 = st.columns(2)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Famosos')
            
            col1.download_button("📊 Descargar Excel", data=buffer.getvalue(), file_name=f"famosos_limpios_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.ms-excel")
            col2.download_button("📋 Descargar Log", data="\n".join(log_text), file_name=f"log_famosos_{datetime.datetime.now().strftime('%Y%m%d')}.log", mime="text/plain")

# ------------------------------------------------------------------------------
# PÁGINA: PORTAFOLIO 3
# ------------------------------------------------------------------------------
elif opcion_menu == "Portafolio 3 (Lugares)":
    st.title("Sistema Relacional - Portafolio 3")
    st.markdown("**División de Datos en 3 Tablas: Lugares, Georeferencias y Direcciones**")
    
    archivo_subido = st.file_uploader("Carga tu dataset de Lugares (.TXT)", type=["txt", "TXT"])
    
    if archivo_subido is not None:
        contenido = archivo_subido.getvalue().decode("utf-8", errors="replace").splitlines()
        
        # === VALIDADOR DE ARCHIVO ESTRICTO ===
        # Exige que las líneas tengan el separador ";"
        es_archivo_correcto = any(";" in linea for linea in contenido[:15])
        
        if not es_archivo_correcto:
            st.error("❌ **¡Archivo Incorrecto o Sin Formato!** El archivo que subiste no corresponde a los Lugares.")
            st.info("💡 Por favor, sube un archivo válido que separe la información con punto y coma (ej: DATOS2026-3.TXT).")
        else:
            lugares_data, georeferencias_data, direcciones_data = [], [], []
            log_text, lugares_vistos = [], set()
            id_contador = 1
            
            log_text.append(f"[{obtener_tiempo()}] - INICIO: Creando Base Relacional.")
            
            for linea in contenido:
                if ";" in linea:
                    partes = linea.split(";")
                    if "Nombre del lugar" in partes[int(0)]:
                        continue
                        
                    if len(partes) >= 3:
                        nombre_lugar = partes[int(0)].strip()
                        direccion_completa = partes[int(1)].strip()
                        coordenadas = partes[int(2)].strip()
                        
                        clave_unica = nombre_lugar + direccion_completa
                        if clave_unica not in lugares_vistos:
                            lugares_vistos.add(clave_unica)
                            lugar_id = id_contador
                            id_contador += 1
                            
                            lugares_data.append({
                                "ID": lugar_id, 
                                "Nombre_Lugar": nombre_lugar,
                                "Hora_Procesamiento": obtener_tiempo()
                            })
                            
                            georeferencias_data.append({
                                "ID": lugar_id, 
                                "ID_Lugar": lugar_id, 
                                "Coordenadas": coordenadas
                            })
                            
                            nom_calle, num_calle, ciudad_prov, pais = procesar_direccion(direccion_completa)
                            direcciones_data.append({
                                "ID": lugar_id,
                                "ID_Lugar": lugar_id,
                                "nombre_calle": nom_calle,
                                "numero_calle": num_calle,
                                "ciudad_estado_provincia": ciudad_prov,
                                "pais": pais
                            })
                            
                            log_text.append(f"[{obtener_tiempo()}] - Dividido: {nombre_lugar} -> Convertido a 3 tablas relacionales.")
                        else:
                            log_text.append(f"[{obtener_tiempo()}] - Ignorado (Duplicado): {nombre_lugar}")
                            
            log_text.append(f"[{obtener_tiempo()}] - FIN: Proceso terminado.")
            
            st.success(f"¡Magia realizada! Se encontraron {len(lugares_data)} lugares únicos y se dividieron en 3 tablas.")
            
            df_lugares = pd.DataFrame(lugares_data)
            df_direcciones = pd.DataFrame(direcciones_data)
            df_geo = pd.DataFrame(georeferencias_data)
            
            tab1, tab2, tab3 = st.tabs(["🏛️ Tabla: Lugares", "📍 Tabla: Direcciones", "🌍 Tabla: Georeferencias"])
            with tab1: st.dataframe(df_lugares, use_container_width=True)
            with tab2: st.dataframe(df_direcciones, use_container_width=True)
            with tab3: st.dataframe(df_geo, use_container_width=True)
                
            col1, col2 = st.columns(2)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_lugares.to_excel(writer, index=False, sheet_name='Lugares')
                df_direcciones.to_excel(writer, index=False, sheet_name='Direcciones')
                df_geo.to_excel(writer, index=False, sheet_name='Georeferencias')
                
            col1.download_button("📊 Descargar Excel Relacional (3 Hojas)", data=buffer.getvalue(), file_name=f"BD_Lugares_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.ms-excel")
            col2.download_button("📋 Descargar Log", data="\n".join(log_text), file_name=f"log_lugares_{datetime.datetime.now().strftime('%Y%m%d')}.log", mime="text/plain")
