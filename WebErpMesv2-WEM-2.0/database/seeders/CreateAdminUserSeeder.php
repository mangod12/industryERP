<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\User;
use Spatie\Permission\Models\Role;
use Spatie\Permission\Models\Permission;

class CreateAdminUserSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        $user = User::firstOrCreate(
            ['email' => 'contact@wem-project.org'], // Condition pour éviter les doublons
            [
                'name' => 'Admin',
                'password' => bcrypt('password'), // Générer un mot de passe sécurisé
            ]
        );
    
        // Vérifier si le rôle existe avant de le créer
        $role = Role::firstOrCreate(['name' => 'Admin']);
    
        // Associer les permissions si elles existent
        $permissions = Permission::pluck('id')->toArray();
        $role->syncPermissions($permissions);
    
        // Associer le rôle à l'utilisateur si ce n'est pas déjà fait
        if (!$user->hasRole($role->name)) {
            $user->assignRole($role);
        }
    }
}
