# transcriber_app/main.py
import os
import sys

from transcriber_app.di import get_process_audio_use_case, get_process_text_use_case
from transcriber_app.config import AVAILABLE_MODES


def mostrar_ayuda():
    print("\n=== TranscriberApp ===")
    print("Procesa audios (.mp3, .webm) o textos (.txt) y genera resúmenes con distintos modos.\n")

    print("USO:")
    print("  python -m transcriber_app.main [audio|texto] [nombre] [modo]\n")

    print("PARÁMETROS:")
    print("  audio        Procesa un archivo .mp3 o .webm desde la carpeta 'audios/'")
    print("  texto        Procesa un archivo .txt desde la carpeta 'transcripts/'")
    print("  nombre       Nombre del archivo SIN extensión")
    print("  modo         Tipo de resumen a generar\n")

    print("MODOS DISPONIBLES:")
    for m in AVAILABLE_MODES:
        print(f"  - {m}")
    print()

    print("EJEMPLOS:")
    print("  Procesar audio:")
    print("    python -m transcriber_app.main audio reunion1 tecnico")
    print("    (usa audios/reunion1.mp3)\n")

    print("  Procesar texto:")
    print("    python -m transcriber_app.main texto sprint1 refinamiento")
    print("    (usa transcripts/sprint1.txt)\n")

    print("SALIDA:")
    print("  - La transcripción (si es audio) se guarda en: transcripts/<nombre>.txt")
    print("  - El resumen final se guarda en: outputs/<nombre>_<modo>.md\n")


def main():

    # ============================
    #   VALIDACIÓN DE ARGUMENTOS
    # ============================
    if len(sys.argv) < 4:
        mostrar_ayuda()
        return

    input_type = sys.argv[1].lower()
    base_name = sys.argv[2]
    mode = sys.argv[3].lower()

    if mode not in AVAILABLE_MODES:
        print(f"❌ Modo no válido: {mode}\n")
        mostrar_ayuda()
        return

    # ============================
    #   RESOLVER RUTA SEGÚN TIPO
    # ============================
    if input_type == "audio":
        # Intentar encontrar el archivo con extensiones comunes
        path = None
        for ext in [".mp3", ".webm", ".wav"]:
            test_path = os.path.join("audios", base_name if base_name.endswith(ext) else base_name + ext)
            if os.path.exists(test_path):
                path = test_path
                break

        if not path:
            # Fallback a .mp3 para el mensaje de error si no existe nada
            path = os.path.join("audios", base_name if base_name.endswith(".mp3") else base_name + ".mp3")

    elif input_type == "texto":
        if not base_name.endswith(".txt"):
            base_name += ".txt"
        path = os.path.join("transcripts", base_name)

    else:
        print("❌ Primer parámetro debe ser 'audio' o 'texto'\n")
        mostrar_ayuda()
        return

    if not os.path.exists(path):
        print(f"❌ No existe el archivo: {path}\n")
        return

    # ============================
    #   INICIALIZAR USE CASES
    # ============================
    if input_type == "audio":
        use_case = get_process_audio_use_case(save_files=True)
    else:
        use_case = get_process_text_use_case(save_files=True)

    # ============================
    #   EJECUTAR USE CASE
    # ============================
    try:
        if input_type == "audio":
            result = use_case.execute(audio_path=path, mode=mode)
        else:
            result = use_case.execute(text=open(path, 'r', encoding='utf-8').read(), mode=mode, filename=os.path.basename(path))

        if result["status"] == "error":
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            sys.exit(1)

        output = f"✅ Transcripción: {result['transcription'][:100]}...\n✅ Resumen: {result['markdown'][:100]}...\n✅ Job ID: {result['job_id']}"

    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(3)

    print(output)


if __name__ == "__main__":
    main()
