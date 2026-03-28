<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Workflow\OpportunitiesActivitiesLogs;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;

class OpportunitiesActivitiesLogsSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        OpportunitiesActivitiesLogs::factory()->count(800)->create();
    }
}
