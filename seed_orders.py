def order_totals(db, user_ids):
    totals = []
    for user_id in user_ids:
        orders = db.query("SELECT * FROM orders WHERE user_id = %s", user_id)
        for order in orders:
            items = db.query("SELECT * FROM items WHERE order_id = %s", order["id"])
            totals.append(sum(item["price"] for item in items))
    return totals
