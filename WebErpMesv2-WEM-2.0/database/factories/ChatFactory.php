<?php

namespace Database\Factories;

use App\Models\Chat;
use App\Models\User;
use App\Models\Workflow\Orders;
use App\Models\Workflow\Quotes;
use App\Models\Planning\Task;
use Illuminate\Database\Eloquent\Factories\Factory;

class ChatFactory extends Factory
{
    // Le modèle associé à cette factory
    protected $model = Chat::class;

    /**
     * Define the model's default state.
     */
    public function definition()
    {
        // Liste des types associés possibles
        $relatedTypes = ['Quotes', 'Orders', 'Task'];

        // Sélection d'un type aléatoire
        $relatedType = $this->faker->randomElement($relatedTypes);

        // En fonction du type, on assigne un ID aléatoire correspondant à un modèle associé
        switch ($relatedType) {
            case 'Quotes':
                $relatedId = Quotes::inRandomOrder()->first()->id ?? 1; // Un ID aléatoire de la table Quotes
                break;
            case 'Orders':
                $relatedId = Orders::inRandomOrder()->first()->id ?? 1; // Un ID aléatoire de la table Orders
                break;
            case 'Task':
                $relatedId = Task::inRandomOrder()->first()->id ?? 1; // Un ID aléatoire de la table Task
                break;
            default:
                $relatedId = 1;
                break;
        }

        return [
            'label' => $this->faker->sentence(3),
            'user_id' => User::inRandomOrder()->first()->id ?? null, // Utilisateur aléatoire ou null
            'related_id' => $relatedId,
            'related_type' => $relatedType,
            'created_at' => now(),
            'updated_at' => now(),
        ];
    }
}

