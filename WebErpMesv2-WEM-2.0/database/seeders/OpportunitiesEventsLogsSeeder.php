<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Workflow\OpportunitiesEventsLogs;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;

class OpportunitiesEventsLogsSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        OpportunitiesEventsLogs::factory()->count(800)->create();
    }
}
