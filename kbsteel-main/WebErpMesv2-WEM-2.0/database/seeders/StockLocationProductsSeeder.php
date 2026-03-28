<?php

namespace Database\Seeders;

use App\Models\Products\StockLocationProducts;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class StockLocationProductsSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        StockLocationProducts::factory()->count(100)->create();
    }
}
