"""Business logic lives here, not in views or serializers.

Views: parse/validate input (serializer) -> call a service -> serialize output.
Services: own transactions, invariants, side effects. Plain functions, keyword args.

Pattern for anything touching stock / balances / money (concurrency-safe):

    @transaction.atomic
    def reserve_stock(*, product_id: UUID, qty: int) -> Product:
        product = Product.objects.select_for_update().get(pk=product_id)  # row lock
        if product.stock < qty:
            raise ValidationError({"qty": "Insufficient stock."})
        product.stock = F("stock") - qty
        product.save(update_fields=["stock", "updated_at"])
        # side effects (emails, webhooks, tasks) only after commit:
        transaction.on_commit(lambda: notify_low_stock.delay(product_id))
        product.refresh_from_db()
        return product

Back the invariant with a DB CheckConstraint (stock >= 0) so a bug can't corrupt data.
"""
