// See LSControlsWidget.h for this class's purpose, pattern and connections.

#include "LSControlsWidget.h"

#include "Brushes/SlateRoundedBoxBrush.h"
#include "Components/Button.h"
#include "Components/NativeWidgetHost.h"
#include "Components/TextBlock.h"
#include "Input/Events.h"
#include "LSGameInstance.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
	const FLinearColor Gold(.94f, .77f, .36f);
	const FLinearColor Ivory(.92f, .91f, .84f);
	const FLinearColor Muted(.54f, .59f, .54f);
	const FSlateRoundedBoxBrush KeyboardCase(FLinearColor(.025f, .038f, .03f), 14.f, FLinearColor(.26f, .31f, .24f), 1.f);
	const FSlateRoundedBoxBrush QuietKey(FLinearColor(.034f, .05f, .04f), 6.f, FLinearColor(.19f, .24f, .19f), 1.f);
	const FSlateRoundedBoxBrush ActiveKey(FLinearColor(.13f, .10f, .04f), 6.f, FLinearColor(.64f, .50f, .23f), 1.f);
	const FSlateRoundedBoxBrush MouseBody(FLinearColor(.025f, .038f, .03f), 38.f, FLinearColor(.53f, .51f, .35f), 1.f);

	struct FKeyboardKey
	{
		const TCHAR* Name;
		float Units = 1.f;
	};

	struct FControlBinding
	{
		FText Keys;
		FText Action;
	};

	TSharedRef<SWidget> DrawKey(const FText& Name, const FSlateFontInfo& Font, bool bActive, float Width, float Height)
	{
		return SNew(SBox).WidthOverride(Width).HeightOverride(Height)
			[
				SNew(SBorder).BorderImage(bActive ? &ActiveKey : &QuietKey).HAlign(HAlign_Center).VAlign(VAlign_Center)
				[SNew(STextBlock).Text(Name).Font(Font).ColorAndOpacity(bActive ? Gold : Muted)]
			];
	}

	TSharedRef<SWidget> DrawKeyboard(const FSlateFontInfo& Font, bool bStone, bool bDandelion)
	{
		const bool bForms = bStone || bDandelion;
		const TSet<FString> BasicKeys = { TEXT("ESC"), TEXT("W"), TEXT("A"), TEXT("S"), TEXT("D"), TEXT("SPACE") };
		const TArray<TArray<FKeyboardKey>> Rows = {
			{ {TEXT("ESC"), 1.3f}, {TEXT("1")}, {TEXT("2")}, {TEXT("3")}, {TEXT("4")}, {TEXT("5")}, {TEXT("6")}, {TEXT("7")}, {TEXT("8")}, {TEXT("9")}, {TEXT("0")}, {TEXT("-")}, {TEXT("=")}, {TEXT("BACKSPACE"), 2.2f} },
			{ {TEXT("TAB"), 1.65f}, {TEXT("Q")}, {TEXT("W")}, {TEXT("E")}, {TEXT("R")}, {TEXT("T")}, {TEXT("Y")}, {TEXT("U")}, {TEXT("I")}, {TEXT("O")}, {TEXT("P")}, {TEXT("[")}, {TEXT("]")}, {TEXT("\\"), 1.85f} },
			{ {TEXT("CAPS"), 1.95f}, {TEXT("A")}, {TEXT("S")}, {TEXT("D")}, {TEXT("F")}, {TEXT("G")}, {TEXT("H")}, {TEXT("J")}, {TEXT("K")}, {TEXT("L")}, {TEXT(";")}, {TEXT("'")}, {TEXT("ENTER"), 2.55f} },
			{ {TEXT("SHIFT"), 2.5f}, {TEXT("Z")}, {TEXT("X")}, {TEXT("C")}, {TEXT("V")}, {TEXT("B")}, {TEXT("N")}, {TEXT("M")}, {TEXT(",")}, {TEXT(".")}, {TEXT("/")}, {TEXT("SHIFT"), 3.f} },
			{ {TEXT("CTRL"), 1.6f}, {TEXT("WIN"), 1.3f}, {TEXT("ALT"), 1.3f}, {TEXT("SPACE"), 6.4f}, {TEXT("ALT"), 1.3f}, {TEXT("FN"), 1.3f}, {TEXT("CTRL"), 2.3f} },
		};
		const TSharedRef<SVerticalBox> Keyboard = SNew(SVerticalBox);
		for (int32 Row = 0; Row < Rows.Num(); ++Row)
		{
			const TSharedRef<SHorizontalBox> Keys = SNew(SHorizontalBox);
			for (int32 Index = 0; Index < Rows[Row].Num(); ++Index)
			{
				const FKeyboardKey& Key = Rows[Row][Index];
				const FString Name(Key.Name);
				const bool bActive = BasicKeys.Contains(Name)
					|| (bForms && (Name == TEXT("1") || Name == TEXT("Q") || Name == TEXT("E")))
					|| (bStone && (Name == TEXT("2") || (Row == 4 && Index == 0)))
					|| (bDandelion && Name == TEXT("3"));
				Keys->AddSlot().AutoWidth().Padding(3.f)
					[DrawKey(FText::FromString(Name), Font, bActive, 56.f * Key.Units - 6.f, 47.f)];
			}
			Keyboard->AddSlot().AutoHeight()[Keys];
		}

		return SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[SNew(SBorder).BorderImage(&KeyboardCase).Padding(15.f)[Keyboard]]
			+ SHorizontalBox::Slot().AutoWidth().Padding(32.f, 0.f, 0.f, 0.f).VAlign(VAlign_Center)
			[
				SNew(SBox).WidthOverride(130.f).HeightOverride(190.f)
				[
					SNew(SBorder).BorderImage(&MouseBody).Padding(11.f, 24.f)
					[
						SNew(SVerticalBox)
						+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
						[
							SNew(SHorizontalBox)
							+ SHorizontalBox::Slot().AutoWidth().Padding(0.f, 0.f, 4.f, 0.f)
							[DrawKey(INVTEXT("LMB"), Font, bStone, 47.f, 57.f)]
							+ SHorizontalBox::Slot().AutoWidth()
							[DrawKey(INVTEXT("RMB"), Font, false, 47.f, 57.f)]
						]
						+ SVerticalBox::Slot().FillHeight(1.f).HAlign(HAlign_Center).VAlign(VAlign_Center)
						[SNew(STextBlock).Text(INVTEXT("MOUSE")).Font(Font).ColorAndOpacity(Gold)]
					]
				]
			];
	}

	TSharedRef<SWidget> BindingColumn(const FText& Title, const TArray<FControlBinding>& Bindings,
		const FSlateFontInfo& HeadingFont, const FSlateFontInfo& BodyFont)
	{
		const TSharedRef<SVerticalBox> Column = SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
			[SNew(STextBlock).Text(Title).Font(HeadingFont).ColorAndOpacity(Gold)];
		for (const FControlBinding& Binding : Bindings)
		{
			Column->AddSlot().AutoHeight().Padding(0.f, 3.f)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().Padding(0.f, 0.f, 12.f, 0.f)
				[DrawKey(Binding.Keys, HeadingFont, true, 126.f, 32.f)]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
				[SNew(STextBlock).Text(Binding.Action).Font(BodyFont).ColorAndOpacity(Ivory)]
			];
		}
		return Column;
	}
}

void ULSControlsWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();

	BackButton->OnClicked.AddDynamic(this, &ULSControlsWidget::HandleBack);
}

void ULSControlsWidget::Open()
{
	const ULSGameInstance* GI = GetGameInstance<ULSGameInstance>();
	const bool bStone = GI && GI->IsFormUnlocked(ESeedForm::Stone);
	const bool bDandelion = GI && GI->IsFormUnlocked(ESeedForm::Dandelion);
	const TArray<FControlBinding> Basics = {
		{ INVTEXT("W A S D"), INVTEXT("Roll") },
		{ INVTEXT("MOUSE"), INVTEXT("Look around") },
		{ INVTEXT("SPACE"), INVTEXT("Jump") },
		{ INVTEXT("ESC"), INVTEXT("Pause") },
	};
	TArray<FControlBinding> Forms, Abilities;
	if (bStone || bDandelion)
	{
		Forms.Add({ INVTEXT("1"), INVTEXT("Seed") });
		if (bStone)
		{
			Forms.Add({ INVTEXT("2"), INVTEXT("Stone Shell") });
			Abilities.Add({ INVTEXT("CTRL / LMB"), INVTEXT("Slam as Stone Shell") });
		}
		if (bDandelion)
		{
			Forms.Add({ INVTEXT("3"), INVTEXT("Dandelion") });
			Abilities.Add({ INVTEXT("HOLD SPACE"), INVTEXT("Glide as Dandelion") });
		}
		Forms.Add({ INVTEXT("Q / E"), INVTEXT("Cycle unlocked forms") });
	}

	FString Controls;
	const TArray<FControlBinding>* Groups[] = { &Basics, &Forms, &Abilities };
	for (const TArray<FControlBinding>* Group : Groups)
	{
		for (const FControlBinding& Binding : *Group)
		{
			Controls += FString::Printf(TEXT("%s   %s\n"), *Binding.Keys.ToString(), *Binding.Action.ToString());
		}
	}
	ControlsText->SetText(FText::FromString(Controls));

	if (UNativeWidgetHost* Layout = Cast<UNativeWidgetHost>(GetWidgetFromName(TEXT("KeyboardLayout"))))
	{
		FSlateFontInfo KeyFont = ControlsText->GetFont();
		KeyFont.Size = 15.f;
		KeyFont.TypefaceFontName = TEXT("Heading");
		FSlateFontInfo BodyFont = ControlsText->GetFont();
		BodyFont.Size = 19.f;
		FSlateFontInfo SectionFont = KeyFont;
		SectionFont.Size = 18.f;
		const TSharedRef<SHorizontalBox> Legend = SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[BindingColumn(INVTEXT("MOVEMENT & MENU"), Basics, SectionFont, BodyFont)];
		if (!Forms.IsEmpty())
		{
			Legend->AddSlot().AutoWidth().Padding(48.f, 0.f, 0.f, 0.f)
				[BindingColumn(INVTEXT("FORMS"), Forms, SectionFont, BodyFont)];
			Legend->AddSlot().AutoWidth().Padding(48.f, 0.f, 0.f, 0.f)
				[BindingColumn(INVTEXT("ABILITIES"), Abilities, SectionFont, BodyFont)];
		}
		Layout->SetContent(
			SNew(SScaleBox).Stretch(EStretch::ScaleToFit).StretchDirection(EStretchDirection::DownOnly)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()[DrawKeyboard(KeyFont, bStone, bDandelion)]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 34.f, 0.f, 0.f)[Legend]
			]);
	}
	SetVisibility(ESlateVisibility::Visible);
	BackButton->SetFocus();
}

FReply ULSControlsWidget::NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
	if (Event.GetKey() == EKeys::Escape)
	{
		HandleBack();
		return FReply::Handled();
	}
	return Super::NativeOnKeyDown(Geometry, Event);
}

void ULSControlsWidget::HandleBack()
{
	SetVisibility(ESlateVisibility::Collapsed);
	OnClosed.Broadcast();
}
