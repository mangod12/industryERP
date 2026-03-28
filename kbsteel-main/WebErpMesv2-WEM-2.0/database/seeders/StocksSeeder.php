<?php

namespace Database\Seeders;

use App\Models\Products\Stocks;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class StocksSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        Stocks::factory()->count(5)->create();
    }
}
