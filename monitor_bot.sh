#!/bin/bash
echo "🤖 AetherBot Live Stats:"
sqlite3 aetherbot.db "SELECT 'Users: ' || COUNT(*) FROM users;"
sqlite3 aetherbot.db "SELECT 'Notes: ' || COUNT(*) FROM user_notes;"
sqlite3 aetherbot.db "SELECT 'Expenses: ' || COUNT(*) FROM expenses;"
echo "Latest activity:"
sqlite3 aetherbot.db "SELECT datetime('now'), 'Last note: ' || note_text FROM user_notes ORDER BY created_at DESC LIMIT 1;"
