#!/usr/bin/env python3
"""
Metadata Detective - Herramienta de análisis de metadatos ocultos en imágenes
Detecta: coordenadas GPS, direcciones IP, datos EXIF, XMP, comentarios ocultos,
información de cámara, fechas, software de edición, y más.
"""

import sys
import os
import re
import struct
import json
import binascii
from datetime import datetime
from pathlib import Path

# Intentar importar bibliotecas opcionales
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False


class Colors:
    """Cores para salida en terminal"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_banner():
    """Muestra el banner de la herramienta"""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ███╗   ███╗███████╗████████╗ █████╗ ██████╗  █████╗      ║
║   ████╗ ████║██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗     ║
║   ██╔████╔██║█████╗     ██║   ███████║██║  ██║███████║     ║
║   ██║╚██╔╝██║██╔══╝     ██║   ██╔══██║██║  ██║██╔══██║     ║
║   ██║ ╚═╝ ██║███████╗   ██║   ██║  ██║██████╔╝██║  ██║     ║
║   ╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝     ║
║           DETECTIVE - Analizador de Metadatos               ║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}"""
    print(banner)


def print_section(title):
    """Imprime una sección con formato"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{Colors.END}")


def print_info(label, value, color=Colors.GREEN):
    """Imprime información con formato"""
    print(f"  {Colors.CYAN}{label}:{Colors.END} {color}{value}{Colors.END}")


def print_warning(msg):
    """Imprime una advertencia"""
    print(f"  {Colors.YELLOW}⚠ {msg}{Colors.END}")


def print_alert(msg):
    """Imprime una alerta importante"""
    print(f"  {Colors.RED}🔴 {msg}{Colors.END}")


def convert_to_degrees(value):
    """Convierte coordenadas GPS de tuplas EXIF a grados decimales"""
    try:
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except (TypeError, ValueError, IndexError):
        return None


def extract_gps_from_exif(exif_data):
    """Extrae coordenadas GPS de los datos EXIF"""
    gps_info = {}
    
    if not exif_data:
        return None
    
    # Buscar el tag GPSInfo (tag 34853)
    gps_tag = 34853
    if gps_tag in exif_data:
        gps_data = exif_data[gps_tag]
        if isinstance(gps_data, dict):
            for key in gps_data.keys():
                decode = GPSTAGS.get(key, key)
                gps_info[decode] = gps_data[key]
    
    if not gps_info:
        return None
    
    lat = None
    lon = None
    
    if "GPSLatitude" in gps_info and "GPSLatitudeRef" in gps_info:
        lat = convert_to_degrees(gps_info["GPSLatitude"])
        if lat is not None and gps_info["GPSLatitudeRef"] == "S":
            lat = -lat
    
    if "GPSLongitude" in gps_info and "GPSLongitudeRef" in gps_info:
        lon = convert_to_degrees(gps_info["GPSLongitude"])
        if lon is not None and gps_info["GPSLongitudeRef"] == "W":
            lon = -lon
    
    if lat is not None and lon is not None:
        return {
            "latitude": lat,
            "longitude": lon,
            "altitud": gps_info.get("GPSAltitude", "N/A"),
            "timestamp": gps_info.get("GPSTimeStamp", "N/A"),
            "datestamp": gps_info.get("GPSDateStamp", "N/A"),
            "map_url": f"https://www.google.com/maps?q={lat},{lon}"
        }
    
    return None


def analyze_with_pil(image_path):
    """Analiza la imagen usando PIL/Pillow"""
    print_section("📷 ANÁLISIS EXIF CON PILLOW")
    
    try:
        img = Image.open(image_path)
        print_info("Formato", img.format)
        print_info("Modo", img.mode)
        print_info("Tamaño", f"{img.width} x {img.height} px")
        print_info("Tamaño del archivo", f"{os.path.getsize(image_path):,} bytes")
        
        # Datos EXIF básicos
        exif_data = img._getexif()
        if exif_data:
            print(f"\n  {Colors.BOLD}Datos EXIF encontrados:{Colors.END}")
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")
                # Truncar valores muy largos
                value_str = str(value)
                if len(value_str) > 80:
                    value_str = value_str[:77] + "..."
                print_info(tag_name, value_str)
            
            # Extraer GPS
            gps = extract_gps_from_exif(exif_data)
            if gps:
                print(f"\n  {Colors.BOLD}{Colors.RED}📍 INFORMACIÓN GPS ENCONTRADA:{Colors.END}")
                print_info("Latitud", f"{gps['latitude']:.6f}°", Colors.RED)
                print_info("Longitud", f"{gps['longitude']:.6f}°", Colors.RED)
                print_info("Altitud", gps['altitud'])
                print_info("URL del mapa", gps['map_url'], Colors.RED)
                print_alert("¡Esta imagen contiene coordenadas GPS!")
            
            return exif_data
        else:
            print_warning("No se encontraron datos EXIF")
            return None
            
    except Exception as e:
        print(f"  {Colors.RED}Error leyendo imagen con PIL: {e}{Colors.END}")
        return None


def analyze_with_piexif(image_path):
    """Analiza la imagen usando piexif (más detallado)"""
    if not PIEXIF_AVAILABLE:
        return None
    
    print_section("🔬 ANÁLISIS EXIF DETALLADO (piexif)")
    
    try:
        exif_dict = piexif.load(image_path)
        
        # Secciones EXIF principales
        sections = {
            "0th": "Información de imagen (IFD principal)",
            "Exif": "Datos EXIF",
            "GPS": "Datos GPS",
            "1st": "Información de imagen thumbnail",
            "Interop": " interoperability"
        }
        
        found_any = False
        for section, description in sections.items():
            if section in exif_dict and exif_dict[section]:
                print(f"\n  {Colors.BOLD}{description}:{Colors.END}")
                for tag_id, value in exif_dict[section].items():
                    try:
                        tag_name = piexif.TAGS[section].get(tag_id, {}).get("name", f"Tag_{tag_id}")
                    except (KeyError, AttributeError):
                        tag_name = f"Tag_{tag_id}"
                    
                    # Decodificar bytes si es necesario
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='replace').strip('\x00')
                        except:
                            value = str(value)
                    
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:97] + "..."
                    
                    print_info(tag_name, value_str)
                    found_any = True
        
        if not found_any:
            print_warning("piexif no encontró metadatos adicionales")
            
    except Exception as e:
        print(f"  {Colors.RED}Error con piexif: {e}{Colors.END}")


def analyze_xmp_data(image_path):
    """Extrae metadatos XMP incrustados en el archivo"""
    print_section("📋 ANÁLISIS XMP (Metadatos XML)")
    
    try:
        with open(image_path, 'rb') as f:
            content = f.read()
        
        # Buscar bloques XMP
        xmp_start = content.find(b'<x:xmpmeta')
        xmp_end = content.find(b'</x:xmpmeta>')
        
        if xmp_start != -1 and xmp_end != -1:
            xmp_data = content[xmp_start:xmp_end + 12].decode('utf-8', errors='replace')
            print(f"  {Colors.GREEN}Datos XMP encontrados:{Colors.END}")
            
            # Extraer campos importantes
            xmp_patterns = {
                "Software": r'<xmp:CreatorTool>([^<]+)</xmp:CreatorTool>',
                "Fecha de creación": r'<xmp:CreateDate>([^<]+)</xmp:CreateDate>',
                "Fecha de modificación": r'<xmp:ModifyDate>([^<]+)</xmp:ModifyDate>',
                "Descripción": r'<dc:description>.*?<rdf:li[^>]*>([^<]+)</rdf:li>',
                "Título": r'<dc:title>.*?<rdf:li[^>]*>([^<]+)</rdf:li>',
                "Creador/Autor": r'<dc:creator>.*?<rdf:li[^>]*>([^<]+)</rdf:li>',
                "Copyright": r'<dc:rights>.*?<rdf:li[^>]*>([^<]+)</rdf:li>',
                "GPS Latitud (XMP)": r'<exif:GPSLatitude>([^<]+)</exif:GPSLatitude>',
                "GPS Longitud (XMP)": r'<exif:GPSLongitude>([^<]+)</exif:GPSLongitude>',
            }
            
            for label, pattern in xmp_patterns.items():
                match = re.search(pattern, xmp_data, re.DOTALL)
                if match:
                    value = match.group(1).strip()
                    if "GPS" in label:
                        print_info(label, value, Colors.RED)
                    else:
                        print_info(label, value)
            
            # Mostrar todo el XMP si es interesante
            rdf_desc = re.search(r'<rdf:Description[^>]*>', xmp_data)
            if rdf_desc:
                print(f"\n  {Colors.YELLOW}Atributos adicionales en XMP:{Colors.END}")
                attrs = re.findall(r'(\w+:\w+)="([^"]*)"', rdf_desc.group())
                for attr_name, attr_value in attrs[:20]:
                    if attr_value and len(attr_value) < 100:
                        print_info(f"  {attr_name}", attr_value)
        else:
            print_warning("No se encontraron datos XMP")
            
    except Exception as e:
        print(f"  {Colors.RED}Error analizando XMP: {e}{Colors.END}")


def search_hidden_ips(image_path):
    """Busca direcciones IP embebidas en los datos del archivo"""
    print_section("🌐 BÚSQUEDA DE DIRECCIONES IP OCULTAS")
    
    try:
        with open(image_path, 'rb') as f:
            content = f.read()
        
        # Patrón para direcciones IP
        ip_pattern = rb'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
        
        # Buscar IPs en texto plano
        ips_found = set()
        for match in re.finditer(ip_pattern, content):
            try:
                ip = match.group().decode('ascii')
                # Filterar IPs comunes de relleno/máscaras
                if not ip.startswith(('0.', '255.', '127.')):
                    ips_found.add(ip)
            except:
                pass
        
        if ips_found:
            print(f"  {Colors.RED}¡Se encontraron {len(ips_found)} dirección(es) IP!{Colors.END}")
            for ip in sorted(ips_found):
                print_info("IP encontrada", ip, Colors.RED)
        else:
            print_info("Resultado", "No se encontraron direcciones IP embebidas")
        
        # Buscar también en el formato de texto del XMP/IPTC
        text_content = content.decode('latin-1', errors='ignore')
        # IPs en formato de texto (a veces separadas por puntos y espacios)
        alt_ip_pattern = r'\b(\d{1,3}\.\s?\d{1,3}\.\s?\d{1,3}\.\s?\d{1,3})\b'
        for match in re.finditer(alt_ip_pattern, text_content):
            potential_ip = match.group().replace(' ', '')
            parts = potential_ip.split('.')
            if all(0 <= int(p) <= 255 for p in parts if p.isdigit()):
                if potential_ip not in ips_found and not potential_ip.startswith(('0.', '255.', '127.')):
                    ips_found.add(potential_ip)
        
        return ips_found
        
    except Exception as e:
        print(f"  {Colors.RED}Error buscando IPs: {e}{Colors.END}")
        return set()


def search_hidden_strings(image_path):
    """Busca strings ocultos en los datos binarios de la imagen"""
    print_section("🔍 BÚSQUEDA DE STRINGS OCULTOS")
    
    try:
        with open(image_path, 'rb') as f:
            content = f.read()
        
        # Extraer strings legibles (mínimo 8 caracteres)
        strings = []
        current_string = bytearray()
        
        for byte in content:
            if 32 <= byte <= 126:  # Caracteres ASCII imprimibles
                current_string.append(byte)
            else:
                if len(current_string) >= 8:
                    strings.append(current_string.decode('ascii', errors='ignore'))
                current_string = bytearray()
        
        if len(current_string) >= 8:
            strings.append(current_string.decode('ascii', errors='ignore'))
        
        # Filtrar strings interesantes
        interesting_keywords = [
            'password', 'passwd', 'pwd', 'user', 'login', 'admin',
            'key', 'token', 'secret', 'api', 'auth', 'credential',
            'copyright', 'author', 'owner', 'comment', 'note',
            'location', 'gps', 'coord', 'lat', 'lon', 'alt',
            'serial', 'device', 'model', 'make', 'version',
            'http', 'https', 'ftp', 'url', 'email', '@',
            'software', 'editor', 'created', 'modified',
            'thumbnail', 'preview', 'raw', 'backup'
        ]
        
        interesting_strings = []
        for s in strings:
            s_lower = s.lower()
            if any(keyword in s_lower for keyword in interesting_keywords):
                if len(s) > 150:
                    s = s[:147] + "..."
                interesting_strings.append(s)
        
        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_strings = []
        for s in interesting_strings:
            if s not in seen:
                seen.add(s)
                unique_strings.append(s)
        
        if unique_strings:
            print(f"  {Colors.GREEN}Se encontraron {len(unique_strings)} strings interesantes:{Colors.END}")
            for i, s in enumerate(unique_strings[:30], 1):
                print(f"    {Colors.CYAN}[{i}]{Colors.END} {s}")
        else:
            print_info("Resultado", "No se encontraron strings ocultos relevantes")
        
        return unique_strings
        
    except Exception as e:
        print(f"  {Colors.RED}Error buscando strings: {e}{Colors.END}")
        return []


def analyze_binary_structure(image_path):
    """Analiza la estructura binaria de la imagen"""
    print_section("🏗️  ANÁLISIS DE ESTRUCTURA BINARIA")
    
    try:
        with open(image_path, 'rb') as f:
            header = f.read(64)  # Primeros 64 bytes
        
        # Detectar firma del archivo
        signatures = {
            b'\xFF\xD8\xFF': "JPEG",
            b'\x89PNG': "PNG",
            b'GIF87a': "GIF",
            b'GIF89a': "GIF",
            b'RIFF': "WebP/RIFF",
            b'BM': "BMP",
            b'II*\x00': "TIFF (Little Endian)",
            b'MM\x00*': "TIFF (Big Endian)",
        }
        
        detected_format = "Desconocido"
        for sig, fmt in signatures.items():
            if header.startswith(sig):
                detected_format = fmt
                break
        
        print_info("Formato detectado", detected_format)
        
        # Buscar datos después del marcador de fin de imagen JPEG
        if detected_format == "JPEG":
            with open(image_path, 'rb') as f:
                content = f.read()
            
            eoi_pos = content.rfind(b'\xFF\xD9')
            if eoi_pos != -1 and eoi_pos < len(content) - 2:
                trailing_data = content[eoi_pos + 2:]
                if trailing_data:
                    print_alert(f"¡Datos encontrados después del marcador EOF de JPEG! ({len(trailing_data)} bytes)")
                    # Intentar decodificar
                    try:
                        decoded = trailing_data.decode('utf-8', errors='replace')[:200]
                        if decoded.strip():
                            print_info("Contenido parcial", decoded[:100])
                    except:
                        pass
        
        # Buscar datos APP segments en JPEG
        if detected_format == "JPEG":
            with open(image_path, 'rb') as f:
                content = f.read()
            
            # Buscar segmentos APP (0xFFE0-0xFFEF)
            pos = 2  # Saltar SOI
            app_segments = []
            while pos < len(content) - 4:
                if content[pos] == 0xFF and 0xE0 <= content[pos + 1] <= 0xEF:
                    seg_type = content[pos + 1]
                    seg_len = struct.unpack('>H', content[pos + 2:pos + 4])[0]
                    seg_data = content[pos + 4:pos + 2 + seg_len]
                    app_segments.append((seg_type, seg_data))
                    pos += 2 + seg_len
                else:
                    pos += 1
            
            if app_segments:
                print(f"\n  {Colors.BOLD}Segmentos APP encontrados:{Colors.END}")
                for seg_type, seg_data in app_segments:
                    seg_name = f"APP{seg_type - 0xE0}"
                    # Identificar segmentos conocidos
                    if b'JFIF' in seg_data[:10]:
                        print_info(seg_name, "JFIF (metadatos JPEG estándar)")
                    elif b'JFXX' in seg_data[:10]:
                        print_info(seg_name, "JFXX (JPEG extendido)")
                    elif b'Exif' in seg_data[:10]:
                        print_info(seg_name, "EXIF", Colors.RED)
                    elif b'http' in seg_data[:50].lower():
                        url_match = re.search(rb'https?://[^\x00]+', seg_data)
                        if url_match:
                            url = url_match.group().decode('ascii', errors='replace')
                            print_info(seg_name, f"URL incrustada: {url}", Colors.RED)
                    elif b'Adobe' in seg_data[:10]:
                        print_info(seg_name, "Adobe")
                    elif len(seg_data) > 5:
                        print_info(seg_name, f"{len(seg_data)} bytes de datos")
        
    except Exception as e:
        print(f"  {Colors.RED}Error en análisis binario: {e}{Colors.END}")


def analyze_iptc_data(image_path):
    """Busca datos IPTC (International Press Telecommunications Council)"""
    print_section("📰 ANÁLISIS IPTC (Metadatos editoriales)")
    
    try:
        with open(image_path, 'rb') as f:
            content = f.read()
        
        # Los datos IPTC están marcados con 0x1C
        iptc_records = []
        pos = 0
        while True:
            pos = content.find(b'\x1c', pos)
            if pos == -1 or pos + 5 > len(content):
                break
            # Verificar que parece un registro IPTC válido
            record_type = content[pos + 1]
            dataset = content[pos + 2]
            if record_type in (1, 2):  # Registros válidos
                data_len = struct.unpack('>H', content[pos + 3:pos + 5])[0]
                if pos + 5 + data_len <= len(content) and data_len < 32768:
                    data = content[pos + 5:pos + 5 + data_len]
                    iptc_records.append((record_type, dataset, data))
            pos += 1
        
        if iptc_records:
            print(f"  {Colors.GREEN}Se encontraron {len(iptc_records)} registros IPTC:{Colors.END}")
            for record_type, dataset, data in iptc_records:
                try:
                    decoded = data.decode('utf-8', errors='replace').strip()
                    if decoded and len(decoded) < 200:
                        print_info(f"Registro {record_type}/{dataset}", decoded)
                except:
                    pass
        else:
            print_info("Resultado", "No se encontraron datos IPTC")
            
    except Exception as e:
        print(f"  {Colors.RED}Error analizando IPTC: {e}{Colors.END}")


def analyze_file_entropy(image_path):
    """Analiza la entropía del archivo para detectar posible esteganografía"""
    print_section("🎲 ANÁLISIS DE ENTROPÍA (Esteganografía)")
    
    try:
        with open(image_path, 'rb') as f:
            content = f.read()
        
        # Calcular entropía de Shannon
        if len(content) == 0:
            print_warning("Archivo vacío")
            return
        
        freq = [0] * 256
        for byte in content:
            freq[byte] += 1
        
        import math
        entropy = 0
        file_size = len(content)
        for count in freq:
            if count > 0:
                p = count / file_size
                entropy -= p * math.log2(p)
        
        print_info("Entropía de Shannon", f"{entropy:.4f} bits/byte")
        print_info("Máximo teórico", "8.0000 bits/byte")
        print_info("Porcentaje", f"{(entropy/8)*100:.1f}%")
        
        # Interpretación
        if entropy > 7.8:
            print_alert("¡Entropía muy alta! Posible archivo cifrado o datos ocultos")
        elif entropy > 7.5:
            print_warning("Entropía elevada. Posible datos ocultos o compresión alta")
        else:
            print_info("Entropía normal", "No se detectan patrones de esteganografía evidentes")
        
        # Analizar los últimos bytes (LSB steganografía común)
        last_bytes = content[-1024:] if len(content) >= 1024 else content
        lsb_bits = ''.join(str(b & 1) for b in last_bytes[:64])
        print_info("Muestra LSB (últimos bytes)", f"{lsb_bits[:32]}...")
        
    except Exception as e:
        print(f"  {Colors.RED}Error calculando entropía: {e}{Colors.END}")


def generate_report(image_path, all_data):
    """Genera un reporte resumen"""
    print_section("📊 RESUMEN DEL ANÁLISIS")
    
    print(f"  {Colors.BOLD}Archivo analizado:{Colors.END} {image_path}")
    print(f"  {Colors.BOLD}Tamaño:{Colors.END} {os.path.getsize(image_path):,} bytes")
    print(f"  {Colors.BOLD}Fecha de análisis:{Colors.END} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    hallazgos = []
    
    if all_data.get('gps'):
        hallazgos.append(("📍 GPS", f"Coordenadas: {all_data['gps']['latitude']:.4f}, {all_data['gps']['longitude']:.4f}", Colors.RED))
    if all_data.get('ips'):
        hallazgos.append(("🌐 IPs", f"{len(all_data['ips'])} encontrada(s)", Colors.RED))
    if all_data.get('xmp'):
        hallazgos.append(("📋 XMP", "Metadatos XMP presentes", Colors.YELLOW))
    if all_data.get('iptc'):
        hallazgos.append(("📰 IPTC", "Datos editoriales presentes", Colors.YELLOW))
    
    print(f"\n  {Colors.BOLD}Hallazgos clave:{Colors.END}")
    if hallazgos:
        for icon, desc, color in hallazgos:
            print(f"    {color}{icon}{Colors.END} {desc}")
    else:
        print(f"    {Colors.YELLOW}No se detectaron metadatos sensibles{Colors.END}")
    
    print(f"\n  {Colors.BOLD}Recomendaciones:{Colors.END}")
    if all_data.get('gps'):
        print(f"    {Colors.RED}• Esta imagen puede revelar tu ubicación exacta{Colors.END}")
    if all_data.get('ips'):
        print(f"    {Colors.RED}• Se encontraron direcciones IP que podrían identificarte{Colors.END}")
    if not hallazgos:
        print(f"    {Colors.GREEN}• La imagen parece limpia de metadatos sensibles{Colors.END}")
    else:
        print(f"    • Considera eliminar metadatos antes de compartir")


def main():
    """Función principal"""
    print_banner()
    
    # Verificar argumentos
    if len(sys.argv) < 2:
        print(f"  {Colors.YELLOW}Uso: python {sys.argv[0]} <imagen> [opciones]{Colors.END}")
        print(f"  {Colors.CYAN}Ejemplo: python {sys.argv[0]} foto.jpg{Colors.END}")
        print(f"  {Colors.CYAN}Opciones:{Colors.END}")
        print(f"    --full    Análisis completo (todos los métodos)")
        print(f"    --gps     Solo buscar GPS")
        print(f"    --ip      Solo buscar IPs")
        print(f"    --strings Solo buscar strings ocultos")
        print(f"    --json    Exportar resultados en JSON")
        sys.exit(1)
    
    image_path = sys.argv[1]
    full_analysis = '--full' in sys.argv or len(sys.argv) == 2
    json_output = '--json' in sys.argv
    
    # Verificar que el archivo existe
    if not os.path.isfile(image_path):
        print(f"  {Colors.RED}Error: El archivo '{image_path}' no existe{Colors.END}")
        sys.exit(1)
    
    # Verificar dependencias
    if not PIL_AVAILABLE:
        print(f"  {Colors.YELLOW}Advertencia: PIL/Pillow no está instalado.{Colors.END}")
        print(f"  {Colors.YELLOW}Instálalo con: pip install Pillow{Colors.END}\n")
    
    all_data = {}
    
    # Análisis con PIL
    if PIL_AVAILABLE:
        exif_data = analyze_with_pil(image_path)
        if exif_data:
            gps = extract_gps_from_exif(exif_data)
            if gps:
                all_data['gps'] = gps
    
    # Análisis detallado con piexif
    if PIEXIF_AVAILABLE and full_analysis:
        analyze_with_piexif(image_path)
    
    # Análisis XMP
    if full_analysis:
        analyze_xmp_data(image_path)
    
    # Búsqueda de IPs
    if full_analysis or '--ip' in sys.argv:
        ips = search_hidden_ips(image_path)
        if ips:
            all_data['ips'] = list(ips)
    
    # Búsqueda de strings ocultos
    if full_analysis or '--strings' in sys.argv:
        strings = search_hidden_strings(image_path)
        if strings:
            all_data['strings'] = strings[:20]
    
    # Análisis binario
    if full_analysis:
        analyze_binary_structure(image_path)
    
    # Análisis IPTC
    if full_analysis:
        analyze_iptc_data(image_path)
    
    # Análisis de entropía
    if full_analysis:
        analyze_file_entropy(image_path)
    
    # GPS específico
    if '--gps' in sys.argv and PIL_AVAILABLE:
        pass  # Ya se analizó arriba
    
    # Generar resumen
    generate_report(image_path, all_data)
    
    # Exportar JSON si se solicita
    if json_output:
        json_path = str(Path(image_path).with_suffix('')) + '_metadata.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, default=str, ensure_ascii=False)
        print(f"\n  {Colors.GREEN}Resultados exportados a: {json_path}{Colors.END}")
    
    print(f"\n{Colors.CYAN}{'='*60}")
    print(f"  Análisis completado.")
    print(f"{'='*60}{Colors.END}\n")


if __name__ == "__main__":
    main()
