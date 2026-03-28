<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\DocumentCodeTemplate;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;

class DocumentCodeTemplateSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $templates = [
            ['document_type' => 'quote', 'template' => 'QT-{year}-{month}-{day}-{id}'],
            ['document_type' => 'order', 'template' => '{day}-OR-{id}'],
            ['document_type' => 'internal-order', 'template' => 'INT-{day}'],
            ['document_type' => 'company', 'template' => 'STE-{id}'],
            ['document_type' => 'delivery', 'template' => 'BON-{id}'],
            ['document_type' => 'purchase', 'template' => 'ACH-{id}'],
            ['document_type' => 'purchase-receipt', 'template' => 'RECIPT-{year}-{id}'],
            ['document_type' => 'purchase-invoice', 'template' => 'FACFOUR-{id}'],
            ['document_type' => 'action', 'template' => 'ACT-{id}'],
            ['document_type' => 'derogation', 'template' => 'DER-{year}-{id}'],
            ['document_type' => 'non-conformities', 'template' => 'NC--{year}-{id}'],
        ];

        foreach ($templates as $template) {
            DocumentCodeTemplate::create($template);
        }
    }
}
