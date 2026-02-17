# ============================================
# Archivo: main.py
# Propósito:
#   - Punto de entrada del sistema (ejecutable)
#   - Inicializa base de datos SQLite
#   - Lanza la interfaz Tkinter
# ============================================

from modulos.bd_sqlite import inicializar_bd  # Crea tablas si no existen
from modulos.ui_tkinter import App            # Ventana principal


def main():
    """
    Función principal.
    - Inicializa BD.
    - Crea la app.
    - Ejecuta el loop Tkinter.
    """
    inicializar_bd()   # Asegura que la BD exista y tenga tablas
    app = App()        # Crea ventana
    app.mainloop()     # Inicia el bucle de eventos de Tkinter


if __name__ == "__main__":
    main()
