<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Document</title>
</head>
<body>
    <h2>{{ ucfirst(class_basename($document)) }} #{{ $document->id }}</h2>
    <p>{!! $messageContent !!}</p>
</body>
</html>
