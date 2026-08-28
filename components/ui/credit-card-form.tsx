"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";

export interface CreditCardFormProps {
  onCardSubmit?: (cardData: {
    cardNumber: string;
    cardHolder: string;
    expiryDate: string;
    cvv: string;
  }) => void;
  className?: string;
}

export const CreditCardForm: React.FC<CreditCardFormProps> = ({
  onCardSubmit,
  className,
}) => {
  const [cardNumber, setCardNumber] = useState("");
  const [cardHolder, setCardHolder] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [cvv, setCvv] = useState("");
  const [isFlipped, setIsFlipped] = useState(false);

  // Determine card type based on number prefix
  const getCardType = (number: string) => {
    const cleanNumber = number.replace(/\s+/g, "");
    if (/^4/.test(cleanNumber)) return "visa";
    if (/^(5[1-5]|2[2-7])/.test(cleanNumber)) return "mastercard";
    if (/^3[47]/.test(cleanNumber)) return "amex";
    if (/^(60|65|81|82)/.test(cleanNumber)) return "rupay";
    return "generic";
  };

  const cardType = getCardType(cardNumber);

  const formatCardNumber = (value: string) => {
    const v = value.replace(/\s+/g, "").replace(/[^0-9]/gi, "");
    const matches = v.match(/\d{4,16}/g);
    const match = (matches && matches[0]) || "";
    const parts = [];

    for (let i = 0, len = match.length; i < len; i += 4) {
      parts.push(match.substring(i, i + 4));
    }

    if (parts.length) {
      return parts.join(" ");
    } else {
      return v;
    }
  };

  const formatExpiry = (value: string) => {
    const v = value.replace(/\s+/g, "").replace(/[^0-9]/gi, "");
    if (v.length >= 2) {
      return `${v.substring(0, 2)}/${v.substring(2, 4)}`;
    }
    return v;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onCardSubmit) {
      onCardSubmit({ cardNumber, cardHolder, expiryDate, cvv });
    }
  };

  return (
    <div className={cn("w-full max-w-md mx-auto space-y-6", className)}>
      {/* 3D Card Preview Container */}
      <div className="relative w-full h-56 perspective-1000">
        <div
          className={cn(
            "w-full h-full duration-700 transform-style-3d transition-transform relative rounded-2xl shadow-2xl overflow-hidden p-6 text-white bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 border border-slate-700/60",
            isFlipped && "rotate-y-180"
          )}
        >
          {/* Card Front */}
          <div className="absolute inset-0 p-6 flex flex-col justify-between backface-hidden bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-900">
            {/* Ambient Watermark Grid & Glow */}
            <div className="absolute -right-10 -bottom-10 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
            
            <div className="flex justify-between items-center z-10">
              {/* EMV Metallic Chip */}
              <div className="w-12 h-9 rounded-md bg-gradient-to-tr from-amber-200 via-yellow-400 to-amber-500 p-1 flex flex-col justify-between shadow-md">
                <div className="w-full h-1/3 border-b border-amber-600/40" />
                <div className="w-full h-1/3 border-b border-amber-600/40" />
              </div>

              {/* Card Type Brand Logo */}
              <div className="text-xl font-bold tracking-wider">
                {cardType === "visa" && <span className="italic font-serif text-2xl text-blue-300">VISA</span>}
                {cardType === "mastercard" && (
                  <div className="flex -space-x-2">
                    <div className="w-7 h-7 rounded-full bg-red-500/90" />
                    <div className="w-7 h-7 rounded-full bg-amber-400/90" />
                  </div>
                )}
                {cardType === "amex" && <span className="font-mono text-cyan-300">AMEX</span>}
                {cardType === "rupay" && <span className="font-bold text-orange-400">RuPay</span>}
                {cardType === "generic" && <span className="text-slate-400 text-sm uppercase">CREDIT/DEBIT</span>}
              </div>
            </div>

            {/* Card Number */}
            <div className="my-auto z-10">
              <div className="text-2xl font-mono tracking-widest drop-shadow-md">
                {cardNumber || "•••• •••• •••• ••••"}
              </div>
            </div>

            {/* Card Holder & Expiry */}
            <div className="flex justify-between items-end z-10 text-xs font-mono uppercase tracking-wider">
              <div>
                <div className="text-slate-400 text-[10px]">Card Holder</div>
                <div className="font-semibold text-sm truncate max-w-[180px]">
                  {cardHolder || "FULL NAME"}
                </div>
              </div>
              <div className="text-right">
                <div className="text-slate-400 text-[10px]">Expires</div>
                <div className="font-semibold text-sm">{expiryDate || "MM/YY"}</div>
              </div>
            </div>
          </div>

          {/* Card Back (Flipped view for CVV) */}
          <div className="absolute inset-0 p-6 flex flex-col justify-between backface-hidden rotate-y-180 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800">
            {/* Magnetic Stripe */}
            <div className="absolute top-6 left-0 w-full h-12 bg-black" />

            {/* Signature & CVV Strip */}
            <div className="mt-20 w-full bg-slate-200 h-10 rounded px-4 flex items-center justify-end text-black font-mono font-bold tracking-widest text-sm">
              <span className="text-xs text-slate-500 mr-3">CVV</span>
              {cvv || "•••"}
            </div>

            <div className="text-[10px] text-slate-400 font-mono text-center">
              This card is non-transferable and subject to cardholder agreement.
            </div>
          </div>
        </div>
      </div>

      {/* Input Form Fields */}
      <form onSubmit={handleSubmit} className="space-y-4 text-left">
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
            Card Number
          </label>
          <input
            type="text"
            maxLength={19}
            placeholder="1234 5678 9012 3456"
            value={cardNumber}
            onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
            className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-sm font-mono focus:ring-2 focus:ring-blue-500 outline-none"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
            Cardholder Name
          </label>
          <input
            type="text"
            placeholder="e.g. THARA KESHAVA REDDY"
            value={cardHolder}
            onChange={(e) => setCardHolder(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-sm uppercase focus:ring-2 focus:ring-blue-500 outline-none"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Expiry Date
            </label>
            <input
              type="text"
              maxLength={5}
              placeholder="MM/YY"
              value={expiryDate}
              onChange={(e) => setExpiryDate(formatExpiry(e.target.value))}
              className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-sm font-mono focus:ring-2 focus:ring-blue-500 outline-none"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              CVV / CVC
            </label>
            <input
              type="password"
              maxLength={4}
              placeholder="•••"
              value={cvv}
              onFocus={() => setIsFlipped(true)}
              onBlur={() => setIsFlipped(false)}
              onChange={(e) => setCvv(e.target.value.replace(/[^0-9]/g, ""))}
              className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-sm font-mono focus:ring-2 focus:ring-blue-500 outline-none"
              required
            />
          </div>
        </div>

        <button
          type="submit"
          className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-md transition-colors text-sm"
        >
          Pay & Authorize Card
        </button>
      </form>
    </div>
  );
};

export default CreditCardForm;
