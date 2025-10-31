from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os

app = Flask(__name__)
app.secret_key = "agristock_secret"
DB = "agristock.db"

# ---------- DATABASE INIT ----------
def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'user'
    )
    """)
    # Stock table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stock(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT,
        quantity INTEGER,
        godown TEXT,
        location TEXT,
        contact TEXT,
        added_by TEXT
    )
    """)
    conn.commit()

    # ✅ Create admin account if not exists
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users(username, password, role) VALUES('admin', 'admin123', 'admin')")
        print("✅ Admin account created (username: admin, password: admin123)")
    conn.commit()
    conn.close()


# ---------- ROUTES ----------
@app.route('/')
def home():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM stock")
    data = cur.fetchall()
    conn.close()
    return render_template("index.html", data=data)


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM stock
        WHERE product LIKE ? OR godown LIKE ?
    """, (f'%{query}%', f'%{query}%'))
    data = cur.fetchall()
    conn.close()
    return render_template("index.html", data=data, search_query=query)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users(username,password) VALUES(?,?)",(u,p))
            conn.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for('login'))
        except:
            flash("Username already exists.")
        conn.close()
    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("SELECT username, password, role FROM users WHERE username=? AND password=?", (u, p))
        user = cur.fetchone()
        conn.close()
        if user:
            session['user'] = user[0]
            session['role'] = user[2]
            flash(f"Welcome back, {user[0]}!")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials!")
    return render_template("login.html")


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user' not in session:
        flash("Please log in to change your password.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username=?", (session['user'],))
        user = cur.fetchone()

        if user and user[0] == old_password:
            cur.execute("UPDATE users SET password=? WHERE username=?", (new_password, session['user']))
            conn.commit()
            conn.close()
            flash("✅ Password changed successfully!")
            return redirect(url_for('dashboard'))
        else:
            conn.close()
            flash("❌ Incorrect old password. Please try again.")
            return redirect(url_for('change_password'))

    return render_template("change_password.html")

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']

        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()

        if user:
            cur.execute("UPDATE users SET password=? WHERE username=?", (new_password, username))
            conn.commit()
            conn.close()
            flash("✅ Password reset successful! You can now log in.")
            return redirect(url_for('login'))
        else:
            conn.close()
            flash("❌ Username not found. Please try again.")
            return redirect(url_for('forgot_password'))

    return render_template("forgot_password.html")



@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM stock")
    data = cur.fetchall()
    conn.close()
    return render_template("dashboard.html", data=data)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        product = request.form['product']
        quantity = request.form['quantity']
        godown = request.form['godown']
        location = request.form['location']
        contact = request.form['contact']
        added_by = session['user']
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("INSERT INTO stock(product,quantity,godown,location,contact,added_by) VALUES(?,?,?,?,?,?)",
                    (product, quantity, godown, location, contact, added_by))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template("add_product.html")

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM stock WHERE id=?", (id,))
    item = cur.fetchone()
    if not item:
        conn.close()
        flash("Product not found.")
        return redirect(url_for('dashboard'))
    if item[6] != session['user']:
        conn.close()
        flash("You can only edit your own products.")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        product = request.form['product']
        quantity = request.form['quantity']
        godown = request.form['godown']
        location = request.form['location']
        contact = request.form['contact']
        cur.execute("""UPDATE stock SET product=?,quantity=?,godown=?,location=?,contact=? WHERE id=?""",
                    (product, quantity, godown, location, contact, id))
        conn.commit()
        conn.close()
        flash("Product updated successfully!")
        return redirect(url_for('dashboard'))
    conn.close()
    return render_template("edit_product.html", item=item)

@app.route('/delete/<int:id>')
def delete(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT added_by FROM stock WHERE id=?", (id,))
    owner = cur.fetchone()
    if not owner:
        flash("Product not found.")
    elif owner[0] != session['user']:
        flash("You can only delete your own products.")
    else:
        cur.execute("DELETE FROM stock WHERE id=?", (id,))
        conn.commit()
        flash("Product deleted successfully!")
    conn.close()
    return redirect(url_for('dashboard'))

if __name__ == "__main__":
    app.run(debug=True)
