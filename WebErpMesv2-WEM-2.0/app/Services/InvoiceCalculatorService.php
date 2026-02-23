<?php
namespace App\Services;

use App\Models\Workflow\Invoices;

class InvoiceCalculatorService
{
    /**
     * @var invoices
     */
    private $invoices;

    public $TotalPrice;
    public $SubTotal;
    public $VatTotal;

    public function __construct(Invoices $invoices)
    {
        $this->invoices = $invoices;
    }

    /**
     * Calculate the total VAT for all invoice lines.
     *
     * This method iterates through all invoice lines, calculates the VAT for each line,
     * and aggregates the VAT amounts by their respective VAT rates. The result is an
     * associative array where the keys are the accounting VAT IDs and the values are
     * arrays containing the VAT rate and the total VAT amount for that rate.
     *
     * @return array An associative array where the keys are the accounting VAT IDs and
     *               the values are arrays containing the VAT rate and the total VAT amount.
     */
    public function getVatTotal()
    {
        $tableauTVA = array();
        $invoicesLines = $this->invoices->invoiceLines;
        foreach ($invoicesLines as $invoicesLine) {
            $TotalCurentLine = ($invoicesLine->qty*$invoicesLine->orderLine->selling_price)-($invoicesLine->qty*$invoicesLine->orderLine->selling_price)*($invoicesLine->orderLine->discount/100);
			$TotalVATCurentLine =  $TotalCurentLine*($invoicesLine->orderLine->VAT['rate']/100) ;
            if(array_key_exists($invoicesLine->orderLine->accounting_vats_id, $tableauTVA)){
                $tableauTVA[$invoicesLine->orderLine->accounting_vats_id][1] += $TotalVATCurentLine;
            }
            else{
                $tableauTVA[$invoicesLine->orderLine->accounting_vats_id] = array($invoicesLine->orderLine->VAT['rate'], $TotalVATCurentLine);
            }
        }
        asort($tableauTVA);
        return $tableauTVA;
    }


    /**
     * Calculate the total price of all invoice lines including VAT and discounts.
     *
     * This method iterates through all invoice lines, calculates the total price for each line
     * by considering the quantity, selling price, discount, and VAT rate, and sums them up to get
     * the total price.
     *
     * @return float The total price of all invoice lines including VAT and discounts.
     */
    public function getTotalPrice()
    {
        $TotalPrice = 0;
        $invoicesLines = $this->invoices->invoiceLines;
        
        foreach ($invoicesLines as $invoicesLine) {
            $TotalPriceLine = ($invoicesLine->qty * $invoicesLine->orderLine->selling_price)-($invoicesLine->qty * $invoicesLine->orderLine->selling_price)*($invoicesLine->orderLine->discount/100);
            $TotalVATPrice = $TotalPriceLine*($invoicesLine->orderLine->VAT['rate']/100);
            $TotalPrice += $TotalPriceLine+$TotalVATPrice;

            
        }
        return $TotalPrice;
    }

    /**
     * Calculate the subtotal for the invoice.
     *
     * This method iterates through all invoice lines and calculates the subtotal
     * by multiplying the quantity of each line item by its selling price, then
     * applying any discounts.
     *
     * @return float The calculated subtotal for the invoice.
     */
    public function getSubTotal()
    {
        $SubTotal = 0;
        $invoicesLines = $this->invoices->invoiceLines;
        foreach ($invoicesLines as $invoicesLine) {
            $SubTotal += ($invoicesLine->qty * $invoicesLine->orderLine->selling_price)-($invoicesLine->qty * $invoicesLine->orderLine->selling_price)*($invoicesLine->orderLine->discount/100);
        }
        return $SubTotal;
    }

}