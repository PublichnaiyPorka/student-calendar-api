from flask import Flask, jsonify, request
import psycopg2
import os
from datetime import datetime, date
import pytz

app = Flask(__name__)

# Подключение к БД
DATABASE_URL = os.environ.get('DATABASE_URL')  # Render задаёт эту переменную автоматически

MOSCOW = pytz.timezone('Europe/Moscow')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Инициализация таблицы (выполните вручную один раз или через init_db)
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS deadlines (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            task TEXT NOT NULL,
            deadline_date DATE NOT NULL
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

# Эндпоинт: добавить дедлайн (опционально, можно и через другой endpoint)
@app.route('/add-deadline', methods=['POST'])
def add_deadline():
    data = request.json
    user_id = data.get('user_id')
    task = data.get('task')
    deadline_str = data.get('deadline')  # ожидаем формат: "2025-12-05"

    try:
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
    except:
        return jsonify({"error": "Неверный формат даты. Используйте YYYY-MM-DD"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO deadlines (user_id, task, deadline_date) VALUES (%s, %s, %s)",
        (user_id, task, deadline)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "ok", "message": "Дедлайн добавлен"})

# Эндпоинт: получить ближайшие дедлайны (главный!)
@app.route('/get-deadlines', methods=['GET'])
def get_deadlines():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"response": "Не указан user_id"}), 400

    try:
        user_id = int(user_id)
    except:
        return jsonify({"response": "Неверный user_id"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    # Получаем дедлайны на ближайшие 30 дней
    cur.execute('''
        SELECT task, deadline_date
        FROM deadlines
        WHERE user_id = %s AND deadline_date >= CURRENT_DATE
        ORDER BY deadline_date ASC
        LIMIT 10;
    ''', (user_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return jsonify({"response": "У вас нет запланированных дедлайнов."})

    today = date.today()
    lines = ["📅 Ваши ближайшие дедлайны:\n"]
    for task, deadline in rows:
        delta = (deadline - today).days
        if delta == 0:
            when = "сегодня"
        elif delta == 1:
            when = "завтра"
        else:
            when = f"через {delta} дн."
        lines.append(f"• {task} — {deadline.strftime('%d.%m.%Y')} ({when})")

    return jsonify({"response": "\n".join(lines)})

# Эндпоинт для инициализации БД (вызовите один раз при первом запуске)
@app.route('/init-db')
def init():
    init_db()
    return "DB initialized"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)