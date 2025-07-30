def filter_content_under_token_limit(items, max_tokens):
    """Yield as many items as fit under max_tokens (approx)."""
    total = 0
    for item in items:
        tc = estimate_tokens(str(item))
        if total + tc > max_tokens:
            break
        total += tc
        yield item
