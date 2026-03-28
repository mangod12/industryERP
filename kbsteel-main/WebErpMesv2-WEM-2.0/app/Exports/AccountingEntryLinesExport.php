<?php

namespace App\Exports;

use App\Models\Accounting\AccountingEntry;
use Maatwebsite\Excel\Concerns\WithMapping;
use Maatwebsite\Excel\Concerns\WithHeadings;
use Maatwebsite\Excel\Concerns\FromCollection;

class AccountingEntryLinesExport implements FromCollection , WithHeadings, WithMapping
{
    
    private $AccountingEntryId;

    Public function __construct($AccountingEntryId)
    {
        $this->AccountingEntryId = $AccountingEntryId;
    }

    public function headings(): array
    {
        return [
            'JOURNAL_CODE',
            'JOURNAL_LABEL',
            'SEQUENCE_NUMBER',
            'ACCOUNTING_DATE',
            'ACCOUNT_NUMBER',
            'ACCOUNT_LABEL',
            'JUSTIFICATION_REFERENCE',
            'JUSTIFICATION_DATE',
            'AUXILIARY_ACCOUNT_NUMBER',
            'AUXILIARY_ACCOUNT_LABEL',
            'DOCUMENT_REFERENCE',
            'DOCUMENT_DATE',
            'ENTRY_LABEL',
            'DEBIT_AMOUNT',
            'CREDIT_AMOUNT',
            'ENTRY_LETTERING',
            'LETTERING_DATE',
            'VALIDATION_DATE',
            'CURRENCY_CODE',
            'INVOICE_LINE_ID',
            'PURCHASE_INVOICE_LINE_ID',
        ];
    }

    public function map($AccountingEntry): array
    {
        return [
            $AccountingEntry->journal_code,
            $AccountingEntry->journal_label,
            $AccountingEntry->sequence_number,
            $AccountingEntry->accounting_date->format('Y-m-d'), // Format de date
            $AccountingEntry->account_number,
            $AccountingEntry->account_label,
            $AccountingEntry->justification_reference,
            $AccountingEntry->justification_date->format('Y-m-d'), // Format de date
            $AccountingEntry->auxiliary_account_number,
            $AccountingEntry->auxiliary_account_label,
            $AccountingEntry->document_reference,
            $AccountingEntry->document_date->format('Y-m-d'), // Format de date
            $AccountingEntry->entry_label,
            $AccountingEntry->debit_amount,
            $AccountingEntry->credit_amount,
            $AccountingEntry->entry_lettering,
            optional($AccountingEntry->lettering_date)->format('Y-m-d'), // Peut être null, on utilise `optional()`
            $AccountingEntry->validation_date->format('Y-m-d'), // Format de date
            $AccountingEntry->currency_code,
            $AccountingEntry->invoice_line_id,
            $AccountingEntry->purchase_invoice_line_id,
        ];
    }

    public function collection()
    {
        return AccountingEntry::whereIn('id', $this->AccountingEntryId)->get();
        
    }
}