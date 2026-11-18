#include "CollapsingStoneComponent.h"

#include "Components/AudioComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "SeedBall.h"
#include "TimerManager.h"

UCollapsingStoneComponent::UCollapsingStoneComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = false;
}

void UCollapsingStoneComponent::BeginPlay()
{
	Super::BeginPlay();
	TArray<AActor*> Actors;
	for (AActor* Support : SupportActors)
		if (IsValid(Support) && Support != GetOwner()) Actors.AddUnique(Support);
	Actors.Add(GetOwner());
	for (AActor* Actor : Actors)
	{
		Pieces.Add(Actor);
		OriginalPoses.Add(Actor->GetActorTransform());
		OriginalCollision.Add(Actor->GetActorEnableCollision());
		OriginalHidden.Add(Actor->IsHidden());
		TInlineComponentArray<UStaticMeshComponent*> Meshes(Actor);
		for (UStaticMeshComponent* Mesh : Meshes) Mesh->SetMobility(EComponentMobility::Movable);
	}

	FVector Origin, Extent;
	GetOwner()->GetActorBounds(false, Origin, Extent);
	SurfaceTop = Origin.Z + Extent.Z;
	Surface = GetOwner()->FindComponentByClass<UStaticMeshComponent>();
	if (Surface)
	{
		Surface->SetNotifyRigidBodyCollision(true);
		Surface->OnComponentHit.AddDynamic(this, &UCollapsingStoneComponent::HandleStep);
	}
}

void UCollapsingStoneComponent::HandleStep(UPrimitiveComponent* HitComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComp, FVector NormalImpulse, const FHitResult& Hit)
{
	ASeedBall* Visitor = Cast<ASeedBall>(OtherActor);
	if (!Visitor || Visitor->IsDead() || bTriggered || bCollapsing) return;
	// Side impacts must not consume a pillar before the player lands on its top.
	if (Visitor->GetActorLocation().Z < SurfaceTop || Hit.ImpactPoint.Z < SurfaceTop - 45.f
		|| FMath::Abs(Hit.ImpactNormal.Z) < 0.5f) return;
	Ball = Visitor;
	Ball->OnRespawned.AddUniqueDynamic(this, &UCollapsingStoneComponent::Rebuild);
	bTriggered = true;
	WarningElapsed = 0.f;
	SetComponentTickEnabled(true);
	if (ShakeSound) ShakeAudio = UGameplayStatics::SpawnSoundAtLocation(this, ShakeSound,
		OriginalPoses.Last().GetLocation(), FRotator::ZeroRotator, 0.75f, FMath::FRandRange(0.97f, 1.03f));
	GetWorld()->GetTimerManager().SetTimer(CollapseTimer, this, &UCollapsingStoneComponent::BeginCollapse,
		FMath::Max(0.01f, CollapseDelay), false);
}

void UCollapsingStoneComponent::BeginCollapse()
{
	bCollapsing = true;
	FallElapsed = 0.f;
	if (IsValid(ShakeAudio)) ShakeAudio->FadeOut(0.06f, 0.f);
	if (FallSound) FallAudio = UGameplayStatics::SpawnSoundAtLocation(this, FallSound,
		OriginalPoses.Last().GetLocation(), FRotator::ZeroRotator, 0.9f, FMath::FRandRange(0.97f, 1.03f));
	for (const TWeakObjectPtr<AActor>& Piece : Pieces)
		if (Piece.IsValid()) Piece->SetActorEnableCollision(false);
	SetComponentTickEnabled(true);
}

void UCollapsingStoneComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (!bCollapsing)
	{
		WarningElapsed += DeltaTime;
		const float Strength = 1.f + 2.f * FMath::Clamp(WarningElapsed / FMath::Max(0.01f, CollapseDelay), 0.f, 1.f);
		for (int32 Index = 0; Index < Pieces.Num(); ++Index)
		{
			if (!Pieces[Index].IsValid()) continue;
			FTransform Pose = OriginalPoses[Index];
			const float Phase = WarningElapsed * 65.f + Index * 0.7f;
			Pose.AddToTranslation(FVector(FMath::Sin(Phase) * Strength, FMath::Cos(Phase * 1.3f) * Strength, 0.f));
			Pieces[Index]->SetActorTransform(Pose, false, nullptr, ETeleportType::TeleportPhysics);
		}
		return;
	}
	FallElapsed += DeltaTime;
	for (int32 Index = 0; Index < Pieces.Num(); ++Index)
	{
		if (!Pieces[Index].IsValid()) continue;
		const float Alpha = FMath::Clamp((FallElapsed - Index * 0.025f) / FMath::Max(0.1f, FallDuration), 0.f, 1.f);
		FTransform Pose = OriginalPoses[Index];
		const float Side = Index % 2 ? -1.f : 1.f;
		Pose.AddToTranslation(FVector(Side * 35.f * Alpha, 15.f * Alpha, -FallDistance * Alpha * Alpha));
		Pose.ConcatenateRotation(FRotator(Side * 12.f * Alpha, 5.f * Alpha, -Side * 8.f * Alpha).Quaternion());
		Pieces[Index]->SetActorTransform(Pose, false, nullptr, ETeleportType::TeleportPhysics);
	}
	if (FallElapsed >= FallDuration + Pieces.Num() * 0.025f)
	{
		for (const TWeakObjectPtr<AActor>& Piece : Pieces)
			if (Piece.IsValid()) Piece->SetActorHiddenInGame(true);
		SetComponentTickEnabled(false);
	}
}

void UCollapsingStoneComponent::Rebuild()
{
	GetWorld()->GetTimerManager().ClearTimer(CollapseTimer);
	SetComponentTickEnabled(false);
	bTriggered = false;
	bCollapsing = false;
	FallElapsed = 0.f;
	WarningElapsed = 0.f;
	if (IsValid(ShakeAudio)) ShakeAudio->Stop();
	if (IsValid(FallAudio)) FallAudio->Stop();
	for (int32 Index = 0; Index < Pieces.Num(); ++Index)
	{
		if (!Pieces[Index].IsValid()) continue;
		Pieces[Index]->SetActorTransform(OriginalPoses[Index], false, nullptr, ETeleportType::TeleportPhysics);
		Pieces[Index]->SetActorHiddenInGame(OriginalHidden[Index]);
		Pieces[Index]->SetActorEnableCollision(OriginalCollision[Index]);
	}
}

void UCollapsingStoneComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	GetWorld()->GetTimerManager().ClearTimer(CollapseTimer);
	if (IsValid(ShakeAudio)) ShakeAudio->Stop();
	if (IsValid(FallAudio)) FallAudio->Stop();
	if (IsValid(Surface)) Surface->OnComponentHit.RemoveDynamic(this, &UCollapsingStoneComponent::HandleStep);
	if (IsValid(Ball)) Ball->OnRespawned.RemoveDynamic(this, &UCollapsingStoneComponent::Rebuild);
	Super::EndPlay(EndPlayReason);
}
