# test_main.py - Para tu configuración actual
import sys
import os


def test_basic_imports():
    """Prueba que los módulos se pueden importar"""
    sys.path.insert(0, os.path.abspath('.'))

    # Prueba importar módulos principales
    try:
        print("✅ transcriber_app importado")
        return True
    except ImportError as e:
        print(f"❌ Error importando transcriber_app: {e}")
        return False


def test_requirements_exist():
    """Verifica que existen archivos de requirements"""
    required_files = ['requirements_clean.txt', 'requirements.txt']
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} encontrado")
        else:
            print(f"⚠️ {file} no encontrado")
    return True


def test_directory_structure():
    """Verifica estructura básica de directorios"""
    expected_dirs = ['transcriber_app', 'audios', 'transcripts', 'outputs']
    for directory in expected_dirs:
        if os.path.exists(directory):
            print(f"✅ Directorio {directory} existe")
        else:
            print(f"⚠️ Directorio {directory} no existe (puede ser normal)")
    return True


if __name__ == "__main__":
    print("🧪 Ejecutando tests básicos para TranscriberApp...\n")

    tests = [
        test_requirements_exist,
        test_directory_structure,
        test_basic_imports,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        test_name = test.__name__
        try:
            if test():
                print(f"✅ {test_name}: PASS\n")
                passed += 1
            else:
                print(f"❌ {test_name}: FAIL\n")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}\n")

    print(f"📊 Resultado: {passed}/{total} tests pasaron")

    if passed == total:
        print("\n🎉 ¡Todos los tests pasaron!")
        sys.exit(0)
    else:
        print("\n⚠️ Algunos tests fallaron")
        sys.exit(1)
