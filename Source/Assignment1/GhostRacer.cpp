// See GhostRacer.h for this class's purpose and connections.

#include "GhostRacer.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "LSDefaultMeshes.h"
#include "LSGameMode.h"
#include "SeedBall.h"

AGhostRacer::AGhostRacer()
{
	PrimaryActorTick.bCanEverTick = true;
#if WITH_EDITORONLY_DATA
	// It follows the player across the whole level, so World Partition must keep it loaded.
	bIsSpatiallyLoaded = false;
#endif

	Ghost = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Ghost"));
	SetRootComponent(Ghost);
	Ghost->SetMobility(EComponentMobility::Movable);
	Ghost->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Ghost->SetCastShadow(false);
	Ghost->SetStaticMesh(LSDefaultMeshes::Sphere());
}

FString AGhostRacer::SlotName() const
{
	return TEXT("Ghost_") + UGameplayStatics::GetCurrentLevelName(this);
}

void AGhostRacer::BeginPlay()
{
	Super::BeginPlay();

	Best = Cast<ULSGhostSave>(UGameplayStatics::LoadGameFromSlot(SlotName(), 0));
	if (Best && Best->Points.Num() < 2)
	{
		Best = nullptr;
	}
	SetActorHiddenInGame(Best == nullptr);

	if (ALSGameMode* GameMode = GetWorld()->GetAuthGameMode<ALSGameMode>())
	{
		GameMode->OnLevelCompleted.AddDynamic(this, &AGhostRacer::HandleLevelCompleted);
	}
}

void AGhostRacer::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	const ALSGameMode* GameMode = GetWorld()->GetAuthGameMode<ALSGameMode>();
	if (!GameMode || bDone)
	{
		return;
	}
	if (!Ball)
	{
		Ball = Cast<ASeedBall>(UGameplayStatics::GetPlayerPawn(this, 0));
		if (!Ball)
		{
			return;
		}
		// The same size as the player's ball. The sphere mesh is 100 cm across.
		SetActorScale3D(FVector(Ball->GetRootComponent()->Bounds.SphereRadius / 50.f));
	}

	const float Time = GameMode->GetLevelTime();

	// Record a point each time the level clock passes another interval.
	while (Recording.Num() <= Time / SampleInterval && Recording.Num() * SampleInterval < MaxRecordSeconds)
	{
		Recording.Add(Ball->GetActorLocation());
	}

	if (Best)
	{
		// Replay: blend between the two recorded points around this moment, and vanish at the ghost's finish.
		const float Index = Time / Best->SampleInterval;
		const int32 Low = FMath::FloorToInt32(Index);
		if (Low + 1 >= Best->Points.Num())
		{
			SetActorHiddenInGame(true);
			return;
		}
		SetActorLocation(FMath::Lerp(Best->Points[Low], Best->Points[Low + 1], Index - Low));
	}
}

void AGhostRacer::HandleLevelCompleted()
{
	bDone = true;
	const ALSGameMode* GameMode = GetWorld()->GetAuthGameMode<ALSGameMode>();
	const float Time = GameMode ? GameMode->GetLevelTime() : 0.f;
	if (Recording.Num() < 2 || (Best && Best->TimeSeconds <= Time))
	{
		return;
	}
	ULSGhostSave* Save = Cast<ULSGhostSave>(UGameplayStatics::CreateSaveGameObject(ULSGhostSave::StaticClass()));
	Save->TimeSeconds = Time;
	Save->Points = Recording;
	Save->SampleInterval = SampleInterval;
	UGameplayStatics::SaveGameToSlot(Save, SlotName(), 0);
}
