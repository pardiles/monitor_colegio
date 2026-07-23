#!/bin/bash
# =============================================================================
# Limpieza periódica del disco EC2.
# Ejecutar semanalmente (cron: 0 4 * * 0 = domingos 4 AM UTC)
#
# Cron entry:
#   0 4 * * 0 /opt/monitor-colegio/cleanup.sh >> /var/log/monitor-cleanup.log 2>&1
# =============================================================================

cd /opt/monitor-colegio
echo "$(date) - Inicio limpieza"

# 1. Outbox enviados (>1 hora)
find data/outbox/ -name "*.json" -mmin +60 -exec rm -f {} \; 2>/dev/null
echo "  ✅ Outbox limpiado"

# 2. Archivos temporales
rm -f /tmp/qr_* /tmp/vincular_* /tmp/pairing* 2>/dev/null
echo "  ✅ /tmp limpiado"

# 3. PDFs de attachments viejos (>30 días)
find data/attachments/ -name "*.pdf" -mtime +30 -exec rm -f {} \; 2>/dev/null
find data/attachments/ -name "*.jpg" -mtime +30 -exec rm -f {} \; 2>/dev/null
echo "  ✅ Attachments viejos limpiados"

# 4. Logs grandes (truncar a últimas 1000 líneas)
for logfile in /var/log/monitor-colegio.log /var/log/monitor-cleanup.log; do
    if [ -f "$logfile" ] && [ $(wc -l < "$logfile") -gt 1000 ]; then
        tail -500 "$logfile" > "${logfile}.tmp" && mv "${logfile}.tmp" "$logfile"
    fi
done
echo "  ✅ Logs truncados"

# 5. Journalctl viejo (>7 días)
journalctl --vacuum-time=7d 2>/dev/null
echo "  ✅ Journalctl limpiado"

# 6. Bot context viejos legacy (si ya existe en subcarpeta)
for ctx in data/bot_context_*.json; do
    if [ -f "$ctx" ]; then
        user_id=$(basename "$ctx" | sed 's/bot_context_//;s/.json//')
        if [ -f "data/${user_id}/bot_context.json" ]; then
            # Ya migrado a subcarpeta, el legacy es redundante pero lo dejamos
            # (wa_handler todavía lo lee)
            :
        fi
    fi
done

# 7. Cache compartido expirado (>30 días sin actualizar)
find data/shared/ -name "*.json" -mtime +30 -exec rm -f {} \; 2>/dev/null
echo "  ✅ Cache compartido expirado limpiado"

# 8. Pip cache
pip cache purge 2>/dev/null
echo "  ✅ Pip cache limpiado"

# Reporte final
echo "  Disco:"
df -h / | tail -1
echo "$(date) - Limpieza completada"
