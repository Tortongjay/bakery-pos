from flask import Flask, render_template, request, redirect
import datetime
import pandas as pd

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        item = request.form['item']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])

        total = quantity * price
        time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        df = pd.DataFrame([[time, item, quantity, price, total]],
                          columns=['Time', 'Item', 'Quantity', 'Price', 'Total'])
        df.to_csv('sales.csv', mode='a', header=not pd.io.common.file_exists('sales.csv'), index=False)

        return redirect('/')

    return render_template('index.html')

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)


