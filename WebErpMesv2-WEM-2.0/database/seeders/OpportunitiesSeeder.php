<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Workflow\Opportunities;

class OpportunitiesSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        Opportunities::factory()->count(800)->create();
    }
}
