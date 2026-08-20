---
name: discount-rounding
description: Required rounding policy for discounted prices
type: project
---

Discounted prices are always quantized to cents with `decimal.ROUND_DOWN`. This is a
contractual compatibility rule; do not substitute the Decimal context default,
`ROUND_HALF_EVEN`, or `ROUND_HALF_UP`.
