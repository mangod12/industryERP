<!DOCTYPE html>
<html>
<head>
    <title>Bienvenue sur WebErpMesv2</title>
</head>
<body>
    <h2>Bienvenue {{ $userName }} !</h2>

    <p>Votre compte a été créé avec succès.</p>
    <p>Vous pouvez vous connecter avec les informations suivantes :</p>

    <ul>
        <li><strong>Email :</strong> {{ $userEmail }}</li>
    </ul>

    <p><a href="{{ route('login') }}">Se connecter</a></p>

    <p>Merci d'utiliser WEM !</p>
</body>
</html>
