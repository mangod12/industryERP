<?php

namespace App\Services;

use App\Models\Workflow\Leads;
use Illuminate\Support\Facades\DB;

class LeadsKPIService
{
    /**
     * Get the rate of leads data grouped by status.
     *
     * @return \Illuminate\Support\Collection
     */
    public function getLeadsDataRate()
    {
        return DB::table('leads')
                    ->select('statu', DB::raw('count(*) as leadsCountRate'))
                    ->groupBy('statu')
                    ->get();
    }

    /**
     * Get the count of leads grouped by priority.
     *
     * @return \Illuminate\Support\Collection
     */
    public function getLeadsCountByPriority()
    {
        return Leads::select('priority', DB::raw('count(*) as leadsCount'))
                    ->groupBy('priority')
                    ->get();
    }

    /**
     * Get the count of leads grouped by company.
     *
     * @return \Illuminate\Support\Collection
     */
    public function getLeadsByCompany()
    {
        return Leads::with('companie')
                            ->select('companies_id', DB::raw('count(*) as count'))
                            ->groupBy('companies_id')
                            ->limit(10)
                            ->get();
    }


    /**
     * Get the total count of leads.
     *
     * @return int
     */
    public function getLeadsCount()
    {
        return Leads::count();
    }

    
    /**
     * Get the count of leads by user.
     *
     * @return \Illuminate\Support\Collection
     */
    public function getLeadsCountByUser()
    {
        return Leads::select('user_id', 'statu', \DB::raw('count(*) as total'))
                ->with('UserManagement:id,name') // Load the UserManagement relationship with the id and name fields
                ->whereIn('statu', [1, 2, 3, 4, 5, 6]) // Statuses ranging from 1 to 6
                ->groupBy('user_id', 'statu')
                ->get()
                ->groupBy('user_id');
    }

}
