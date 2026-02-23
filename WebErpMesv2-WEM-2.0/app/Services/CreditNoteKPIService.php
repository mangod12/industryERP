<?php

namespace App\Services;

use Illuminate\Support\Facades\DB;

class CreditNoteKPIService
{
    /**
     * Retrieves the rate of grouped credit notes by status.
     *
     * @return \Illuminate\Support\Collection
     */
    public function getCreditNotesDataRate()
    {
        return DB::table('credit_notes')
                    ->select('statu', DB::raw('count(*) as CreditNotesCountRate'))
                    ->groupBy('statu')
                    ->get();
    }

    /**
     * Get a monthly recap of credit notes for a given year.
     *
     * This function retrieves the monthly summary of credit notes for the specified year.
     * It joins the `credit_note_lines` table with the `order_lines` table to calculate
     * the total sum of credit notes for each month, considering the selling price, quantity,
     * and discount of the order lines.
     *
     * @param int $year The year for which to retrieve the credit notes monthly recap.
     * @return \Illuminate\Support\Collection A collection of objects containing the month and the total sum of credit notes for that month.
     */
    public function getCreditNotesMonthlyRecap($year)
    {
        return DB::table('credit_note_lines')
                    ->join('order_lines', 'credit_note_lines.order_line_id', '=', 'order_lines.id')
                    ->selectRaw('
                        MONTH(credit_note_lines.created_at) AS month,
                        SUM((order_lines.selling_price * credit_note_lines.qty)-(order_lines.selling_price * credit_note_lines.qty)*(order_lines.discount/100)) AS orderSum
                    ')
                    ->whereYear('credit_note_lines.created_at', $year)
                    ->groupByRaw('MONTH(credit_note_lines.created_at) ')
                    ->get();
    }

}
