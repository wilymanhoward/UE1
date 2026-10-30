// See LSVolumeBase.h for this class's purpose, pattern and connections.

#include "LSVolumeBase.h"

#include "Components/BoxComponent.h"
#include "SeedBall.h"

ALSVolumeBase::ALSVolumeBase()
{
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	SetRootComponent(Box);
	Box->SetBoxExtent(FVector(200.f));
	Box->SetCollisionProfileName(TEXT("Trigger"));
}

ASeedBall* ALSVolumeBase::GetBallInside() const
{
	TArray<AActor*> Balls;
	Box->GetOverlappingActors(Balls, ASeedBall::StaticClass());
	ASeedBall* Ball = Balls.IsEmpty() ? nullptr : Cast<ASeedBall>(Balls[0]);
	return Ball && !Ball->IsDead() ? Ball : nullptr;
}
