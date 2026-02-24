import sys
import os

# Add src to path
src_dir = os.path.join(os.getcwd(), 'src')
sys.path.insert(0, src_dir)

# Disable Qt display
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

print("=" * 60)
print("Testing App Import and Basic UI Creation")
print("=" * 60)

try:
    print("\n[1/3] Importing app module...")
    from app import PurifyAIApp
    print("      OK")

    print("\n[2/3] Creating QApplication...")
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    print("      OK")

    print("\n[3/3] Creating PurifyAIApp instance...")
    window = PurifyAIApp(app)
    print("      OK")

    print("\n" + "=" * 60)
    print("SUCCESS: App created without errors")
    print("=" * 60)

except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
