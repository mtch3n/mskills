"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export default function NewInvoicePage() {
  const [customer, setCustomer] = useState("")
  const [amount, setAmount] = useState("")

  return (
    <main className="mx-auto max-w-md p-6">
      <h1 className="mb-6 text-2xl font-semibold">New invoice</h1>
      <form className="grid gap-4">
        <div className="grid gap-2">
          <Label htmlFor="customer">Customer</Label>
          <Input id="customer" value={customer} onChange={(e) => setCustomer(e.target.value)} />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="amount">Amount</Label>
          <Input id="amount" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </div>
        <div>
          <Button type="submit">Create invoice</Button>
        </div>
      </form>
    </main>
  )
}
