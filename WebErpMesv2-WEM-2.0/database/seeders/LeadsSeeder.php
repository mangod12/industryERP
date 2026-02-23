<?php

namespace Database\Seeders;

use App\Models\Workflow\Leads;
use Illuminate\Database\Seeder;

class LeadsSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        Leads::factory()->count(1000)->create();
    }
}
