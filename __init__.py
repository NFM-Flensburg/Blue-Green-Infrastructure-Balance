def classFactory(iface):
    """Load NettoNullBilanz class from file."""
    from .netto_null_bilanz import NettoNullBilanz
    return NettoNullBilanz(iface)
